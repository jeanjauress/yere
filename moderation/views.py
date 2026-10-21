from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from listings.models import Listing
from notifications.services import notify
from orders.models import Order
from reviews.models import Review

from .audit import log_action
from .forms import DecisionForm, ReportForm
from .models import AuditLog, Report

User = get_user_model()
staff_required = user_passes_test(lambda u: u.is_authenticated and u.is_staff, login_url="accounts:login")


# --- Côté utilisateur : signaler ---

@login_required
def report_listing(request, pk):
    listing = get_object_or_404(Listing, pk=pk)
    return _report(request, listing=listing, reported_user=listing.seller, back=listing.get_absolute_url())


@login_required
def report_user(request, username):
    target = get_object_or_404(User, username=username)
    if target == request.user:
        raise Http404
    return _report(request, reported_user=target, back=f"/compte/vendeur/{target.username}/")


def _report(request, back, listing=None, reported_user=None):
    form = ReportForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        report = form.save(commit=False)
        report.reporter, report.listing, report.reported_user = request.user, listing, reported_user
        report.save()
        messages.success(request, "Merci, votre signalement sera examiné par notre équipe.")
        return redirect(back)
    return render(request, "moderation/report_form.html", {
        "form": form, "listing": listing, "reported_user": reported_user, "back": back,
    })


# --- Côté administration ---

@staff_required
def dashboard(request):
    since = timezone.now() - timedelta(days=30)
    orders = Order.objects.exclude(status=Order.Status.CANCELLED)
    stats = {
        "users": User.objects.count(),
        "new_users": User.objects.filter(date_joined__gte=since).count(),
        "listings": Listing.objects.public().count(),
        "new_listings": Listing.objects.filter(created_at__gte=since).count(),
        "orders": orders.count(),
        "orders_30": orders.filter(created_at__gte=since).count(),
        "gmv_30": orders.filter(created_at__gte=since).aggregate(s=Sum("total_amount"))["s"] or 0,
        "open_reports": Report.objects.filter(status=Report.Status.OPEN).count(),
        "suspended_users": User.objects.filter(is_suspended=True).count(),
        "suspended_listings": Listing.objects.filter(status=Listing.Status.SUSPENDED).count(),
    }
    by_status = Order.objects.values("status").annotate(n=Count("id")).order_by("status")
    return render(request, "moderation/dashboard.html", {
        "stats": stats, "by_status": [(Order.Status(r["status"]).label, r["n"]) for r in by_status],
        "reports": Report.objects.filter(status=Report.Status.OPEN).select_related("reporter", "listing",
                                                                                   "reported_user")[:10],
        "logs": AuditLog.objects.select_related("actor")[:10],
    })


@staff_required
def reports(request):
    status = request.GET.get("statut", Report.Status.OPEN)
    qs = Report.objects.select_related("reporter", "listing", "reported_user", "handled_by")
    if status in Report.Status.values:
        qs = qs.filter(status=status)
    return render(request, "moderation/reports.html", {
        "page": Paginator(qs, 30).get_page(request.GET.get("page")), "status": status,
        "statuses": Report.Status.choices,
    })


@staff_required
def report_detail(request, pk):
    report = get_object_or_404(Report.objects.select_related("reporter", "listing", "reported_user"), pk=pk)
    form = DecisionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        action, note = form.cleaned_data["action"], form.cleaned_data["decision"]
        if action == "suspend_listing" and report.listing:
            _suspend_listing(request, report.listing, note)
        elif action == "suspend_user" and report.reported_user:
            _suspend_user(request, report.reported_user, note)
        report.status = Report.Status.DISMISSED if action == "dismiss" else Report.Status.RESOLVED
        report.decision, report.handled_by, report.handled_at = note, request.user, timezone.now()
        report.save()
        log_action(request, f"report.{action}", report, note)
        if report.reporter:
            notify(report.reporter, "moderation",
                   f"Votre signalement a été examiné : {report.get_status_display()}.")
        messages.success(request, "Décision enregistrée.")
        return redirect("moderation:reports")
    return render(request, "moderation/report_detail.html", {"report": report, "form": form})


def _suspend_listing(request, listing, note=""):
    listing.status = Listing.Status.SUSPENDED
    listing.save(update_fields=["status", "updated_at"])
    log_action(request, "listing.suspend", listing, note)
    notify(listing.seller, "moderation", f"Votre annonce « {listing.title} » a été suspendue par la modération.")


def _suspend_user(request, user, note=""):
    if user.is_superuser:
        messages.error(request, "Impossible de suspendre un super-administrateur.")
        return
    user.is_suspended = True
    user.save(update_fields=["is_suspended"])
    log_action(request, "user.suspend", user, note)


@staff_required
def listings(request):
    q = request.GET.get("q", "")
    status = request.GET.get("statut", "")
    qs = Listing.objects.select_related("seller", "category")
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(seller__username__icontains=q))
    if status in Listing.Status.values:
        qs = qs.filter(status=status)
    return render(request, "moderation/listings.html", {
        "page": Paginator(qs, 30).get_page(request.GET.get("page")), "q": q, "status": status,
        "statuses": Listing.Status.choices,
    })


@staff_required
@require_POST
def listing_action(request, pk, action):
    listing = get_object_or_404(Listing, pk=pk)
    if action == "suspendre":
        _suspend_listing(request, listing, request.POST.get("note", ""))
    elif action == "retablir":
        listing.status = Listing.Status.PUBLISHED if listing.quantity else Listing.Status.SOLD
        listing.save(update_fields=["status", "updated_at"])
        log_action(request, "listing.restore", listing)
        notify(listing.seller, "moderation", f"Votre annonce « {listing.title} » est de nouveau visible.")
    elif action == "supprimer":
        listing.status = Listing.Status.DELETED
        listing.save(update_fields=["status", "updated_at"])
        log_action(request, "listing.delete", listing)
        notify(listing.seller, "moderation", f"Votre annonce « {listing.title} » a été supprimée par la modération.")
    else:
        raise Http404
    messages.success(request, "Action effectuée.")
    back = request.POST.get("back")
    if back and url_has_allowed_host_and_scheme(back, {request.get_host()}, request.is_secure()):
        return redirect(back)
    return redirect("moderation:listings")


@staff_required
def users(request):
    q = request.GET.get("q", "")
    qs = User.objects.annotate(n_listings=Count("listings", distinct=True)).order_by("-date_joined")
    if q:
        qs = qs.filter(Q(username__icontains=q) | Q(email__icontains=q) | Q(phone__icontains=q))
    if request.GET.get("suspendus"):
        qs = qs.filter(is_suspended=True)
    return render(request, "moderation/users.html", {
        "page": Paginator(qs, 30).get_page(request.GET.get("page")), "q": q,
    })


@staff_required
@require_POST
def user_action(request, pk, action):
    target = get_object_or_404(User, pk=pk)
    if action == "suspendre":
        _suspend_user(request, target, request.POST.get("note", ""))
    elif action == "reactiver":
        target.is_suspended = False
        target.is_active = True
        target.save(update_fields=["is_suspended", "is_active"])
        log_action(request, "user.reactivate", target)
    else:
        raise Http404
    messages.success(request, "Action effectuée.")
    return redirect("moderation:users")


@staff_required
def orders(request):
    status = request.GET.get("statut", "")
    qs = Order.objects.select_related("buyer", "seller")
    if status in Order.Status.values:
        qs = qs.filter(status=status)
    q = request.GET.get("q", "")
    if q:
        qs = qs.filter(Q(order_number__icontains=q) | Q(buyer__username__icontains=q) |
                       Q(seller__username__icontains=q))
    return render(request, "moderation/orders.html", {
        "page": Paginator(qs, 30).get_page(request.GET.get("page")), "status": status, "q": q,
        "statuses": Order.Status.choices,
    })


@staff_required
def reviews(request):
    qs = Review.objects.select_related("author", "seller", "order")
    return render(request, "moderation/reviews.html", {"page": Paginator(qs, 30).get_page(request.GET.get("page"))})


@staff_required
@require_POST
def review_toggle(request, pk):
    review = get_object_or_404(Review, pk=pk)
    review.is_hidden = not review.is_hidden
    review.save(update_fields=["is_hidden"])
    log_action(request, "review.hide" if review.is_hidden else "review.show", review)
    return redirect("moderation:reviews")


@staff_required
def audit(request):
    qs = AuditLog.objects.select_related("actor")
    action = request.GET.get("action", "")
    if action:
        qs = qs.filter(action__startswith=action)
    return render(request, "moderation/audit.html", {
        "page": Paginator(qs, 50).get_page(request.GET.get("page")), "action": action,
    })
