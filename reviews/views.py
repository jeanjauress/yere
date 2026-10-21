from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render

from notifications.services import notify
from orders.models import Order

from .forms import ReviewForm


@login_required
def create(request, number):
    # Seul l'acheteur d'une commande livrée peut laisser un avis, une seule fois.
    order = get_object_or_404(Order, order_number=number, buyer=request.user)
    if not order.is_reviewable:
        messages.error(request, "Cette commande ne peut pas (ou plus) être évaluée.")
        return redirect(order)
    form = ReviewForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        review = form.save(commit=False)
        review.order, review.author, review.seller = order, request.user, order.seller
        try:
            review.save()
        except IntegrityError:
            messages.error(request, "Vous avez déjà évalué cette commande.")
            return redirect(order)
        notify(order.seller, "review", f"{request.user.username} vous a laissé un avis ({review.rating}/5).",
               f"/compte/vendeur/{order.seller.username}/")
        messages.success(request, "Merci pour votre avis !")
        return redirect(order)
    return render(request, "reviews/form.html", {"form": form, "order": order})


@login_required
def mine(request):
    return render(request, "reviews/mine.html", {
        "received": request.user.reviews_received.select_related("author", "order"),
        "written": request.user.reviews_written.select_related("seller", "order"),
    })
