from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .models import Notification


@login_required
def notification_list(request):
    qs = Notification.objects.filter(user=request.user)
    page = Paginator(qs, 30).get_page(request.GET.get("page"))
    return render(request, "notifications/list.html", {"page": page})


@login_required
def open_notification(request, pk):
    n = get_object_or_404(Notification, pk=pk, user=request.user)
    if not n.is_read:
        n.is_read = True
        n.save(update_fields=["is_read"])
    if n.url and url_has_allowed_host_and_scheme(n.url, {request.get_host()}, request.is_secure()):
        return redirect(n.url)
    return redirect("notifications:list")


@login_required
@require_POST
def mark_all_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect("notifications:list")
