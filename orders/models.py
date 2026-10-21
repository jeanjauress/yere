import secrets

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class CartItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart_items")
    listing = models.ForeignKey("listings.Listing", on_delete=models.CASCADE, related_name="cart_items")
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "article du panier"
        ordering = ["added_at"]
        constraints = [models.UniqueConstraint(fields=["user", "listing"], name="unique_cart_item")]

    @property
    def subtotal(self):
        return self.listing.price * self.quantity


def generate_order_number():
    return f"CMD-{timezone.now():%Y%m%d}-{secrets.token_hex(3).upper()}"


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "En attente de confirmation"
        CONFIRMED = "confirmed", "Confirmée"
        PREPARING = "preparing", "En préparation"
        SHIPPED = "shipped", "Expédiée / remise au transporteur"
        DELIVERED = "delivered", "Livrée"
        CANCELLED = "cancelled", "Annulée"
        REFUNDED = "refunded", "Remboursée"

    class PaymentStatus(models.TextChoices):
        UNPAID = "unpaid", "Non payée"
        PENDING = "pending", "Paiement en cours"
        PAID = "paid", "Payée"
        FAILED = "failed", "Échec du paiement"
        REFUNDED = "refunded", "Remboursée"

    # Transitions autorisées : statut -> statuts suivants possibles.
    TRANSITIONS = {
        Status.PENDING: {Status.CONFIRMED, Status.CANCELLED},
        Status.CONFIRMED: {Status.PREPARING, Status.SHIPPED, Status.CANCELLED},
        Status.PREPARING: {Status.SHIPPED, Status.CANCELLED},
        Status.SHIPPED: {Status.DELIVERED},
        Status.DELIVERED: {Status.REFUNDED},
        Status.CANCELLED: set(),
        Status.REFUNDED: set(),
    }

    order_number = models.CharField("numéro", max_length=24, unique=True, default=generate_order_number)
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="purchases",
                              verbose_name="acheteur")
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="sales",
                               verbose_name="vendeur")
    items_amount = models.PositiveIntegerField("montant des articles (XOF)")
    delivery_fee = models.PositiveIntegerField("frais de livraison (XOF)", default=0)
    total_amount = models.PositiveIntegerField("montant total (XOF)")
    status = models.CharField("statut", max_length=12, choices=Status.choices, default=Status.PENDING)
    payment_method = models.CharField("moyen de paiement", max_length=20, default="cod")
    payment_status = models.CharField("paiement", max_length=10, choices=PaymentStatus.choices,
                                      default=PaymentStatus.UNPAID)
    # Livraison
    delivery_mode = models.CharField("mode de livraison", max_length=20)
    recipient_name = models.CharField("destinataire", max_length=120)
    recipient_phone = models.CharField("téléphone", max_length=20)
    delivery_address = models.CharField("adresse / point de livraison", max_length=255)
    commune = models.CharField("commune", max_length=80, blank=True)
    city = models.CharField("ville", max_length=80)
    tracking_note = models.CharField("suivi de livraison", max_length=255, blank=True)
    buyer_note = models.TextField("message au vendeur", max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "commande"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["buyer", "-created_at"]),
            models.Index(fields=["seller", "-created_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return self.order_number

    def get_absolute_url(self):
        return reverse("orders:detail", args=[self.order_number])

    def can_transition(self, new_status):
        return new_status in self.TRANSITIONS.get(self.status, set())

    @property
    def delivery_mode_label(self):
        return settings.DELIVERY_MODES.get(self.delivery_mode, {}).get("label", self.delivery_mode)

    @property
    def is_reviewable(self):
        return self.status == self.Status.DELIVERED and not hasattr(self, "review")


class OrderItem(models.Model):
    """Copie de l'article au moment de l'achat : l'historique ne change pas si l'annonce est modifiée."""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    listing = models.ForeignKey("listings.Listing", on_delete=models.SET_NULL, null=True, related_name="order_items")
    title = models.CharField(max_length=120)
    unit_price = models.PositiveIntegerField("prix unitaire (XOF)")
    quantity = models.PositiveIntegerField()

    class Meta:
        verbose_name = "ligne de commande"

    @property
    def subtotal(self):
        return self.unit_price * self.quantity


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        SUCCEEDED = "succeeded", "Réussi"
        FAILED = "failed", "Échoué"
        REFUNDED = "refunded", "Remboursé"

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="payments")
    provider = models.CharField(max_length=30)
    amount = models.PositiveIntegerField("montant (XOF)")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    # Référence externe du prestataire. Aucune donnée de carte ni code Mobile Money n'est stockée.
    reference = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "paiement"
        ordering = ["-created_at"]
