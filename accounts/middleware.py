from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect


class SuspendedUserMiddleware:
    """Déconnecte immédiatement un compte suspendu ou désactivé."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and (user.is_suspended or not user.is_active):
            logout(request)
            messages.error(request, "Votre compte est suspendu. Contactez le support.")
            return redirect("accounts:login")
        return self.get_response(request)
