from django.conf import settings


def site(request):
    data = {"SITE_NAME": settings.SITE_NAME, "ADMIN_URL": settings.ADMIN_URL}
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        from messaging.models import Message
        from notifications.models import Notification
        from orders.models import CartItem

        data["unread_notifications"] = Notification.objects.filter(user=user, is_read=False).count()
        data["unread_messages"] = Message.objects.unread_for(user).count()
        from favorites.models import Favorite

        data["fav_ids"] = set(Favorite.objects.filter(user=user).values_list("listing_id", flat=True))
        data["cart_count"] = CartItem.objects.filter(user=user).count()
    return data
