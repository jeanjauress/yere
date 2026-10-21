from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from listings.models import Listing

from .forms import CheckoutForm, SellerStatusForm
from .models import CartItem, Order
from .services import CheckoutError, cart_summary, change_status, checkout


def _parse_qty(value, default=1):
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return default


@login_required
def cart(request):
    return render(request, "orders/cart.html", cart_summary(request.user))


@login_required
@require_POST
def cart_add(request, pk):
    listing = get_object_or_404(Listing, pk=pk)
    if listing.seller_id == request.user.pk:
        messages.error(request, "Vous ne pouvez pas acheter votre propre article.")
        return redirect(listing)
    if not listing.is_purchasable:
        messages.error(request, "Cet article n'est plus disponible.")
        return redirect(listing)
    qty = _parse_qty(request.POST.get("quantity"))
    item, created = CartItem.objects.get_or_create(user=request.user, listing=listing, defaults={"quantity": 0})
    item.quantity = min(item.quantity + qty, listing.quantity)
    item.save()
    messages.success(request, "Article ajouté au panier.")
    if request.POST.get("buy_now"):
        return redirect("orders:checkout")
    return redirect("orders:cart")


@login_required
@require_POST
def cart_update(request, pk):
    item = get_object_or_404(CartItem.objects.select_related("listing"), pk=pk, user=request.user)
    qty = _parse_qty(request.POST.get("quantity"), item.quantity)
    if qty > item.listing.quantity:
        messages.warning(request, f"Stock disponible : {item.listing.quantity}.")
        qty = max(1, item.listing.quantity)
    item.quantity = qty
    item.save(update_fields=["quantity"])
    return redirect("orders:cart")


@login_required
@require_POST
def cart_remove(request, pk):
    CartItem.objects.filter(pk=pk, user=request.user).delete()
    messages.info(request, "Article retiré du panier.")
    return redirect("orders:cart")


@login_required
def checkout_view(request):
    summary = cart_summary(request.user)
    if not summary["items"]:
        messages.info(request, "Votre panier est vide.")
        return redirect("orders:cart")
    user = request.user
    form = CheckoutForm(request.POST or None, initial={
        "recipient_name": user.get_full_name() or user.username, "recipient_phone": user.phone,
        "city": user.city or "Abidjan", "delivery_mode": "abidjan",
    })
    if request.method == "POST" and form.is_valid():
        if summary["problems"]:
            for p in summary["problems"]:
                messages.error(request, p)
            return redirect("orders:cart")
        try:
            orders = checkout(user, form.cleaned_data)
        except CheckoutError as e:
            messages.error(request, str(e))
            return redirect("orders:cart")
        messages.success(request, f"Commande confirmée ({len(orders)} commande(s) créée(s)).")
        return redirect(orders[0] if len(orders) == 1 else "orders:purchases")
    from django.conf import settings
    n_sellers = len(summary["groups"])
    fees = {k: v["fee"] * n_sellers for k, v in settings.DELIVERY_MODES.items()}
    return render(request, "orders/checkout.html", {**summary, "form": form, "fees": fees,
                                                    "n_sellers": n_sellers})


@login_required
def purchases(request):
    qs = Order.objects.filter(buyer=request.user).select_related("seller").prefetch_related("items")
    return render(request, "orders/list.html", {
        "page": Paginator(qs, 20).get_page(request.GET.get("page")), "mode": "purchases",
    })


@login_required
def sales(request):
    qs = Order.objects.filter(seller=request.user).select_related("buyer").prefetch_related("items")
    status = request.GET.get("statut")
    if status in Order.Status.values:
        qs = qs.filter(status=status)
    return render(request, "orders/list.html", {
        "page": Paginator(qs, 20).get_page(request.GET.get("page")), "mode": "sales",
        "statuses": Order.Status.choices, "status": status,
    })


def _get_order(request, number):
    qs = Order.objects.select_related("buyer", "seller").prefetch_related("items__listing__images", "payments")
    if not request.user.is_staff:
        qs = qs.filter(Q(buyer=request.user) | Q(seller=request.user))
    return get_object_or_404(qs, order_number=number)


@login_required
def detail(request, number):
    order = _get_order(request, number)
    ctx = {"order": order, "is_seller": order.seller_id == request.user.pk,
           "is_buyer": order.buyer_id == request.user.pk}
    if ctx["is_seller"]:
        ctx["status_form"] = SellerStatusForm(order, initial={"tracking_note": order.tracking_note})
    return render(request, "orders/detail.html", ctx)


@login_required
@require_POST
def seller_update(request, number):
    order = _get_order(request, number)
    if order.seller_id != request.user.pk:
        raise Http404
    form = SellerStatusForm(order, request.POST)
    if form.is_valid():
        try:
            change_status(order, form.cleaned_data["status"], request.user, form.cleaned_data["tracking_note"])
            messages.success(request, "Statut mis à jour.")
        except CheckoutError as e:
            messages.error(request, str(e))
    else:
        messages.error(request, "Statut invalide.")
    return redirect(order)


@login_required
@require_POST
def buyer_action(request, number, action):
    order = _get_order(request, number)
    if order.buyer_id != request.user.pk:
        raise Http404
    target = {"annuler": Order.Status.CANCELLED, "recue": Order.Status.DELIVERED}.get(action)
    allowed_from = {Order.Status.CANCELLED: {Order.Status.PENDING}, Order.Status.DELIVERED: {Order.Status.SHIPPED}}
    if target is None or order.status not in allowed_from[target]:
        messages.error(request, "Action impossible pour cette commande.")
    else:
        change_status(order, target, request.user)
        messages.success(request, "Commande mise à jour.")
    return redirect(order)
