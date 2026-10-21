from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailOrUsernameBackend(ModelBackend):
    """Connexion avec le nom d'utilisateur ou l'adresse e-mail."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
        User = get_user_model()
        field = "email__iexact" if "@" in username else "username__iexact"
        user = User.objects.filter(**{field: username}).first()
        if user is None:
            User().set_password(password)  # temps constant
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def user_can_authenticate(self, user):
        return super().user_can_authenticate(user) and not getattr(user, "is_suspended", False)

    def get_user(self, user_id):
        # Les comptes suspendus sont chargés pour que SuspendedUserMiddleware
        # puisse les déconnecter proprement avec un message.
        User = get_user_model()
        user = User._default_manager.filter(pk=user_id).first()
        return user if user and super().user_can_authenticate(user) else None
