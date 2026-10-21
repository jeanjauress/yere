from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

app_name = "accounts"

urlpatterns = [
    path("inscription/", views.signup, name="signup"),
    path("connexion/", views.LoginView.as_view(), name="login"),
    path("deconnexion/", views.logout_view, name="logout"),
    path("verifier/<str:token>/", views.verify_email, name="verify_email"),
    path("verifier-renvoyer/", views.resend_verification, name="resend_verification"),
    path("tableau-de-bord/", views.dashboard, name="dashboard"),
    path("parametres/", views.settings_view, name="settings"),
    path("desactiver/", views.deactivate, name="deactivate"),
    path("mot-de-passe/", auth_views.PasswordChangeView.as_view(
        template_name="accounts/form_page.html",
        extra_context={"title": "Changer le mot de passe"},
        success_url=reverse_lazy("accounts:settings")), name="password_change"),
    path("mot-de-passe/oublie/", auth_views.PasswordResetView.as_view(
        template_name="accounts/form_page.html",
        extra_context={"title": "Mot de passe oublié"},
        email_template_name="accounts/password_reset_email.txt",
        success_url=reverse_lazy("accounts:password_reset_done")), name="password_reset"),
    path("mot-de-passe/envoye/", auth_views.PasswordResetDoneView.as_view(
        template_name="accounts/message_page.html",
        extra_context={"title": "E-mail envoyé",
                       "text": "Si un compte correspond à cette adresse, vous recevrez un lien de réinitialisation."}),
         name="password_reset_done"),
    path("mot-de-passe/reinitialiser/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="accounts/form_page.html",
        extra_context={"title": "Nouveau mot de passe"},
        success_url=reverse_lazy("accounts:password_reset_complete")), name="password_reset_confirm"),
    path("mot-de-passe/termine/", auth_views.PasswordResetCompleteView.as_view(
        template_name="accounts/message_page.html",
        extra_context={"title": "Mot de passe modifié", "text": "Vous pouvez maintenant vous connecter."}),
         name="password_reset_complete"),
    path("vendeur/<str:username>/", views.public_profile, name="profile"),
]
