from django import forms
from django.conf import settings

from listings.templatetags.market import xof

from .models import Order
from .payments import available_methods


class CheckoutForm(forms.Form):
    recipient_name = forms.CharField(label="Nom du destinataire", max_length=120)
    recipient_phone = forms.RegexField(label="Téléphone", max_length=20, regex=r"^\+?[0-9 ]{8,20}$",
                                       error_messages={"invalid": "Numéro de téléphone invalide."})
    delivery_address = forms.CharField(label="Adresse ou point de livraison", max_length=255)
    commune = forms.CharField(label="Commune", max_length=80, required=False)
    city = forms.CharField(label="Ville", max_length=80, initial="Abidjan")
    delivery_mode = forms.ChoiceField(label="Mode de livraison", widget=forms.RadioSelect)
    payment_method = forms.ChoiceField(label="Paiement", widget=forms.RadioSelect)
    buyer_note = forms.CharField(label="Message au vendeur (facultatif)", required=False, max_length=500,
                                 widget=forms.Textarea(attrs={"rows": 2}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["delivery_mode"].choices = [
            (k, f"{v['label']} — {xof(v['fee'])}" if v["fee"] else f"{v['label']} — gratuit")
            for k, v in settings.DELIVERY_MODES.items()
        ]
        self.fields["payment_method"].choices = available_methods()
        self.fields["payment_method"].initial = settings.PAYMENT_METHODS[0]


class SellerStatusForm(forms.Form):
    status = forms.ChoiceField(label="Nouveau statut")
    tracking_note = forms.CharField(label="Note de suivi (transporteur, référence…)", required=False, max_length=255)

    def __init__(self, order, *args, **kwargs):
        super().__init__(*args, **kwargs)
        allowed = order.TRANSITIONS[order.status] - {Order.Status.REFUNDED}
        self.fields["status"].choices = [(s, Order.Status(s).label) for s in Order.Status.values if s in allowed]
