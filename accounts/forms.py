from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

User = get_user_model()


class SignupForm(UserCreationForm):
    accept_terms = forms.BooleanField(label="J'accepte les conditions d'utilisation", required=True)

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "phone")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Un compte existe déjà avec cette adresse e-mail.")
        return email


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Nom d'utilisateur ou e-mail", max_length=254)

    error_messages = {
        "invalid_login": "Identifiants incorrects.",
        "inactive": "Ce compte est désactivé ou suspendu.",
    }


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "phone", "city", "bio", "profile_image")
        widgets = {"bio": forms.Textarea(attrs={"rows": 3})}

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Cette adresse e-mail est déjà utilisée.")
        return email


class DeactivateForm(forms.Form):
    password = forms.CharField(label="Mot de passe", widget=forms.PasswordInput)
    confirm = forms.BooleanField(label="Je confirme vouloir désactiver mon compte")
