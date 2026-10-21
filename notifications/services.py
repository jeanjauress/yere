def notify(user, kind, message, url=""):
    """Crée une notification sur le site. Point d'extension pour e-mail / SMS plus tard."""
    from .models import Notification

    return Notification.objects.create(user=user, kind=kind, message=message[:255], url=url)
