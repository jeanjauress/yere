from collections import defaultdict

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from listings.models import Listing
from notifications.services import notify

from .models import CartItem, Order, OrderItem, Payment
from .payments import get_provider


class CheckoutError(Exception):
    pass


def delivery_fee(mode):
    return settings.DELIVERY_MODES[mode]["fee"]


def cart_summary(user):
    """Regroupe le panier par vendeur. Tous les montants sont recalculés côté serveur."""
    items = list(CartItem.objects.filter(user=user).select_related("listing__seller").prefetch_related("listing__images"))
    groups = defaultdict(list)
    problems = []
    for item in items:
        listing = item.listing
        if not listing.is_purchasable or listing.seller_id == user.pk:
            problems.append(f"« {listing.title} » n'est plus disponible.")
        elif item.quantity > listing.quantity:
            problems.append(f"« {listing.title} » : seulement {listing.quantity} disponible(s).")
        groups[listing.seller].append(item)
    total = sum(i.subtotal for i in items)
    return {"items": items, "groups": dict(groups), "items_total": total, "problems": problems}


def _reserve_stock(listing_id, qty):
    """Décrément conditionnel atomique : échoue si le stock est insuffisant (pas de vente multiple)."""
    updated = Listing.objects.filter(
        pk=listing_id, status=Listing.Status.PUBLISHED, quantity__gte=qty,
    ).update(quantity=F("quantity") - qty)
    if not updated:
        return False
    Listing.objects.filter(pk=listing_id, quantity=0).update(status=Listing.Status.SOLD)
    return True


def checkout(user, delivery):
    """
    Valide le panier : crée une commande par vendeur et réserve le stock,
    le tout dans une seule transaction. Lève CheckoutError si un article
    n'est plus disponible ; dans ce cas rien n'est enregistré.
    """
    mode = delivery["delivery_mode"]
    if mode not in settings.DELIVERY_MODES:
        raise CheckoutError("Mode de livraison invalide.")
    provider = get_provider(delivery["payment_method"])
    orders = []
    with transaction.atomic():
        items = list(CartItem.objects.filter(user=user).select_related("listing__seller"))
        if not items:
            raise CheckoutError("Votre panier est vide.")
        by_seller = defaultdict(list)
        for item in items:
            listing = item.listing
            if listing.seller_id == user.pk:
                raise CheckoutError("Vous ne pouvez pas acheter votre propre article.")
            if not listing.is_purchasable:
                raise CheckoutError(f"« {listing.title} » n'est plus disponible.")
            by_seller[listing.seller].append(item)

        fee = delivery_fee(mode)
        for seller, seller_items in by_seller.items():
            amount = sum(i.listing.price * i.quantity for i in seller_items)
            order = Order.objects.create(
                buyer=user, seller=seller, items_amount=amount, delivery_fee=fee, total_amount=amount + fee,
                payment_method=provider.code, delivery_mode=mode,
                recipient_name=delivery["recipient_name"], recipient_phone=delivery["recipient_phone"],
                delivery_address=delivery["delivery_address"], commune=delivery.get("commune", ""),
                city=delivery["city"], buyer_note=delivery.get("buyer_note", ""),
            )
            for item in seller_items:
                if not _reserve_stock(item.listing_id, item.quantity):
                    raise CheckoutError(f"« {item.listing.title} » vient d'être acheté ou le stock est insuffisant.")
                OrderItem.objects.create(order=order, listing=item.listing, title=item.listing.title,
                                         unit_price=item.listing.price, quantity=item.quantity)
            provider.start(order)
            orders.append(order)
        CartItem.objects.filter(pk__in=[i.pk for i in items]).delete()

    for order in orders:
        notify(order.seller, "order_received", f"Nouvelle commande {order.order_number} de {user.username}.",
               order.get_absolute_url())
        for item in order.items.select_related("listing"):
            if item.listing and item.listing.status == Listing.Status.SOLD:
                notify(order.seller, "item_sold", f"Votre article « {item.title} » est vendu.",
                       order.get_absolute_url())
    return orders


def _restore_stock(order):
    for item in order.items.all():
        if item.listing_id:
            Listing.objects.filter(pk=item.listing_id).update(quantity=F("quantity") + item.quantity)
            Listing.objects.filter(pk=item.listing_id, status=Listing.Status.SOLD, quantity__gt=0) \
                .update(status=Listing.Status.PUBLISHED)


def change_status(order, new_status, actor, tracking_note=None):
    """Applique une transition de statut autorisée, avec remise en stock en cas d'annulation."""
    with transaction.atomic():
        order = Order.objects.get(pk=order.pk)
        if not order.can_transition(new_status):
            raise CheckoutError("Changement de statut non autorisé.")
        order.status = new_status
        if tracking_note is not None:
            order.tracking_note = tracking_note
        if new_status == Order.Status.CANCELLED:
            _restore_stock(order)
            order.payments.filter(status=Payment.Status.PENDING).update(status=Payment.Status.FAILED)
        if new_status == Order.Status.DELIVERED:
            order.delivered_at = timezone.now()
            if order.payment_method == "cod":
                # Paiement à la livraison : l'argent est remis au moment de la livraison.
                for payment in order.payments.filter(status=Payment.Status.PENDING):
                    get_provider("cod").confirm(payment)
                order.payment_status = Order.PaymentStatus.PAID
        if new_status == Order.Status.REFUNDED:
            order.payment_status = Order.PaymentStatus.REFUNDED
            order.payments.filter(status=Payment.Status.SUCCEEDED).update(status=Payment.Status.REFUNDED)
        order.save()

    label = order.get_status_display()
    for user in {order.buyer, order.seller} - {actor}:
        notify(user, "order_status", f"Commande {order.order_number} : {label}.", order.get_absolute_url())
    return order
