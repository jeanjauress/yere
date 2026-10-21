from django import forms

from .models import Review


class ReviewForm(forms.ModelForm):
    rating = forms.TypedChoiceField(label="Note", coerce=int, widget=forms.RadioSelect,
                                    choices=[(i, "★" * i) for i in range(5, 0, -1)])

    class Meta:
        model = Review
        fields = ("rating", "comment")
        widgets = {"comment": forms.Textarea(attrs={"rows": 3, "placeholder": "Comment s'est passée la transaction ?"})}
