from django.contrib import messages as flash
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Max, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from listings.models import Listing
from notifications.services import notify

from .forms import MessageForm
from .models import Block, Conversation, Message

User = get_user_model()


@login_required
def inbox(request):
    user = request.user
    convs = Conversation.for_user(user).select_related("listing", "buyer", "seller").annotate(
        last_at=Max("messages__created_at"),
        unread=Count("messages", filter=Q(messages__read_at__isnull=True) & ~Q(messages__sender=user)),
    ).filter(last_at__isnull=False).order_by("-last_at")
    rows = [{"conv": c, "other": c.other(user), "last": c.messages.last()} for c in convs]
    return render(request, "messaging/inbox.html", {"rows": rows})


@login_required
def start(request, listing_pk):
    """Ouvre (ou reprend) la conversation avec le vendeur d'une annonce."""
    listing = get_object_or_404(Listing.objects.public(), pk=listing_pk)
    if listing.seller_id == request.user.pk:
        flash.info(request, "C'est votre propre annonce.")
        return redirect(listing)
    conv, _ = Conversation.objects.get_or_create(listing=listing, buyer=request.user, seller=listing.seller)
    return redirect("messaging:thread", pk=conv.pk)


@login_required
def thread(request, pk):
    conv = get_object_or_404(Conversation.objects.select_related("listing", "buyer", "seller"), pk=pk)
    if not conv.has_participant(request.user):
        raise Http404
    other = conv.other(request.user)
    blocked = Block.between(request.user, other)
    form = MessageForm(request.POST or None)
    if request.method == "POST":
        if blocked:
            flash.error(request, "Vous ne pouvez pas écrire à cet utilisateur.")
        elif form.is_valid():
            Message.objects.create(conversation=conv, sender=request.user, body=form.cleaned_data["body"])
            conv.save(update_fields=["updated_at"])
            notify(other, "message", f"Nouveau message de {request.user.username}",
                   f"/messages/{conv.pk}/")
            return redirect("messaging:thread", pk=conv.pk)
    conv.messages.filter(read_at__isnull=True).exclude(sender=request.user).update(read_at=timezone.now())
    return render(request, "messaging/thread.html", {
        "conv": conv, "other": other, "msgs": conv.messages.select_related("sender"), "form": form,
        "blocked": blocked, "i_blocked": Block.objects.filter(blocker=request.user, blocked=other).exists(),
    })


@login_required
@require_POST
def toggle_block(request, username):
    other = get_object_or_404(User, username=username)
    if other == request.user:
        raise Http404
    block, created = Block.objects.get_or_create(blocker=request.user, blocked=other)
    if not created:
        block.delete()
        flash.success(request, f"{other.username} est débloqué.")
    else:
        flash.success(request, f"{other.username} est bloqué : vous ne recevrez plus ses messages.")
    nxt = request.POST.get("next")
    if nxt and url_has_allowed_host_and_scheme(nxt, {request.get_host()}, request.is_secure()):
        return redirect(nxt)
    return redirect("messaging:inbox")
