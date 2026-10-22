from django import template

register = template.Library()

# Couleur des pastilles de statut dans l'espace d'administration.
STATUS_CLASSES = {
    "published": "ok", "delivered": "ok", "paid": "ok", "resolved": "ok",
    "pending": "warn", "draft": "warn", "inactive": "warn", "confirmed": "warn", "preparing": "warn",
    "shipped": "warn", "open": "warn", "unpaid": "warn",
    "suspended": "bad", "deleted": "bad", "failed": "bad", "cancelled": "bad", "refunded": "bad",
}


@register.filter
def status_class(value):
    return STATUS_CLASSES.get(value, "")
