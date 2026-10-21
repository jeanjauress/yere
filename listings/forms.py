from django import forms
from django.conf import settings

from .models import Category, Listing
from .validators import validate_image_file


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.FileField):
    widget = MultipleFileInput(attrs={"accept": "image/jpeg,image/png,image/webp"})

    def clean(self, data, initial=None):
        files = data if isinstance(data, (list, tuple)) else ([data] if data else [])
        cleaned = []
        for f in files:
            f = super().clean(f, initial)
            validate_image_file(f)
            cleaned.append(f)
        return cleaned


class ListingForm(forms.ModelForm):
    photos = MultipleImageField(label="Photos", required=False,
                                help_text="JPEG, PNG ou WEBP, 5 Mo maximum par photo.")
    save_as_draft = forms.BooleanField(label="Enregistrer comme brouillon", required=False)

    class Meta:
        model = Listing
        fields = ("title", "category", "description", "brand", "size", "condition",
                  "price", "quantity", "city", "commune")
        widgets = {"description": forms.Textarea(attrs={"rows": 6})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(is_active=True).select_related("parent")
        self.fields["price"].widget.attrs.update({"min": 0, "step": 50})
        self.fields["quantity"].widget.attrs.update({"min": 0})

    def clean(self):
        cleaned = super().clean()
        photos = cleaned.get("photos") or []
        existing = self.instance.images.count() if self.instance.pk else 0
        if existing + len(photos) > settings.LISTING_MAX_IMAGES:
            raise forms.ValidationError(f"{settings.LISTING_MAX_IMAGES} photos maximum par annonce.")
        if not cleaned.get("save_as_draft") and existing + len(photos) == 0:
            self.add_error("photos", "Ajoutez au moins une photo pour publier l'annonce.")
        return cleaned


class SearchForm(forms.Form):
    SORTS = [
        ("recent", "Plus récentes"),
        ("price_asc", "Prix croissant"),
        ("price_desc", "Prix décroissant"),
        ("popular", "Populaires"),
    ]
    q = forms.CharField(required=False, max_length=100)
    category = forms.ModelChoiceField(queryset=Category.objects.filter(is_active=True), required=False,
                                      to_field_name="slug")
    min_price = forms.IntegerField(required=False, min_value=0)
    max_price = forms.IntegerField(required=False, min_value=0)
    condition = forms.ChoiceField(choices=[("", "Tous")] + list(Listing.Condition.choices), required=False)
    brand = forms.CharField(required=False, max_length=80)
    city = forms.CharField(required=False, max_length=80)
    sort = forms.ChoiceField(choices=SORTS, required=False)
