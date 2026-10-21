from django.conf import settings
from django.db import models


class Notification(models.Model):
    class Kind(models.TextChoices):
        MESSAGE = "message", "Nouveau message"
        ORDER_RECEIVED = "order_received", "Commande reçue"
        ORDER_STATUS = "order_status", "Statut de commande"
        ITEM_SOLD = "item_sold", "Article vendu"
        REVIEW = "review", "Nouvel avis"
        MODERATION = "moderation", "Modération"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    message = models.CharField(max_length=255)
    url = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "is_read"])]
