"""
Interface des moyens de paiement.

Pour la V1 seul le paiement à la livraison est actif. Pour brancher un
prestataire Mobile Money / carte (CinetPay, PayDunya, etc.), créer une
classe qui implémente `start()` (redirection vers le prestataire) et
`confirm()` (appelée depuis le webhook signé du prestataire), puis
l'ajouter à PROVIDERS et à settings.PAYMENT_METHODS.

Règle : une commande n'est « payée » que lorsque le prestataire l'a confirmée.
"""
from django.conf import settings
from django.utils import timezone

from .models import Order, Payment


class PaymentProvider:
    code = ""
    label = ""

    def start(self, order):
        """Crée le paiement. Retourne une URL de redirection ou None."""
        raise NotImplementedError

    def confirm(self, payment, reference=""):
        payment.status = Payment.Status.SUCCEEDED
        payment.reference = reference or payment.reference
        payment.confirmed_at = timezone.now()
        payment.save()
        Order.objects.filter(pk=payment.order_id).update(payment_status=Order.PaymentStatus.PAID)


class CashOnDelivery(PaymentProvider):
    code = "cod"
    label = "Paiement à la livraison"

    def start(self, order):
        Payment.objects.create(order=order, provider=self.code, amount=order.total_amount)
        return None


PROVIDERS = {p.code: p for p in [CashOnDelivery()]}


def available_methods():
    return [(code, PROVIDERS[code].label) for code in settings.PAYMENT_METHODS if code in PROVIDERS]


def get_provider(code):
    return PROVIDERS[code]
