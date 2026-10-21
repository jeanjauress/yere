from django import forms

from .models import Report


class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ("reason", "details")
        widgets = {"details": forms.Textarea(attrs={"rows": 3})}


class DecisionForm(forms.Form):
    ACTIONS = [
        ("dismiss", "Classer sans suite"),
        ("suspend_listing", "Suspendre l'annonce"),
        ("suspend_user", "Suspendre le compte"),
        ("resolve", "Marquer comme traité"),
    ]
    action = forms.ChoiceField(label="Décision", choices=ACTIONS)
    decision = forms.CharField(label="Motif / note interne", widget=forms.Textarea(attrs={"rows": 2}), required=False)
