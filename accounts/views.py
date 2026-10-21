from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from listings.models import Listing
from orders.models import Order

from . import ratelimit, tokens
from .forms import DeactivateForm, LoginForm, ProfileForm, SignupForm

User = get_user_model()


def send_verification_email(request, user):
    link = request.build_absolute_uri(reverse("accounts:verify_email", args=[tokens.make_token(user)]))
    send_mail(
        f"{settings.SITE_NAME} — confirmez votre adresse e-mail",
        f"Bonjour {user.username},\n\nConfirmez votre adresse en ouvrant ce lien :\n{link}\n\n"
        "Ce lien est valable 3 jours.",
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
    )


def signup(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        send_verification_email(request, user)
        login(request, user, backend=settings.AUTHENTICATION_BACKENDS[0])
        messages.success(request, "Bienvenue ! Un e-mail de confirmation vous a été envoyé.")
        return redirect("accounts:dashboard")
    return render(request, "accounts/signup.html", {"form": form})


class LoginView(auth_views.LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def post(self, request, *args, **kwargs):
        username = request.POST.get("username", "")
        if ratelimit.is_locked(request, username):
            messages.error(request, "Trop de tentatives. Réessayez dans quelques minutes.")
            return self.get(request, *args, **kwargs)
        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        ratelimit.register_failure(self.request, self.request.POST.get("username", ""))
        return super().form_invalid(form)

    def form_valid(self, form):
        ratelimit.reset(self.request, self.request.POST.get("username", ""))
        return super().form_valid(form)


def verify_email(request, token):
    data = tokens.read_token(token)
    user = data and User.objects.filter(pk=data["uid"], email=data["email"]).first()
    if not user:
        messages.error(request, "Lien de vérification invalide ou expiré.")
        return redirect("listings:home")
    user.email_verified = True
    user.save(update_fields=["email_verified"])
    messages.success(request, "Votre adresse e-mail est confirmée.")
    return redirect("accounts:dashboard" if request.user.is_authenticated else "accounts:login")


@login_required
@require_POST
def resend_verification(request):
    if not request.user.email_verified:
        send_verification_email(request, request.user)
        messages.info(request, "Un nouvel e-mail de confirmation a été envoyé.")
    return redirect("accounts:settings")


@login_required
def dashboard(request):
    user = request.user
    ctx = {
        "listings_count": user.listings.exclude(status=Listing.Status.DELETED).count(),
        "active_count": user.listings.filter(status=Listing.Status.PUBLISHED).count(),
        "favorites_count": user.favorites.count(),
        "purchases": Order.objects.filter(buyer=user).order_by("-created_at")[:5],
        "sales": Order.objects.filter(seller=user).order_by("-created_at")[:5],
        "pending_sales": Order.objects.filter(seller=user, status=Order.Status.PENDING).count(),
        "rating": user.rating_summary(),
    }
    return render(request, "accounts/dashboard.html", ctx)


@login_required
def settings_view(request):
    form = ProfileForm(request.POST or None, request.FILES or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        email_changed = "email" in form.changed_data
        user = form.save(commit=False)
        if email_changed:
            user.email_verified = False
        user.save()
        if email_changed:
            send_verification_email(request, user)
            messages.info(request, "Nouvelle adresse : un e-mail de confirmation a été envoyé.")
        messages.success(request, "Profil mis à jour.")
        return redirect("accounts:settings")
    return render(request, "accounts/settings.html", {"form": form})


@login_required
def deactivate(request):
    form = DeactivateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if not request.user.check_password(form.cleaned_data["password"]):
            form.add_error("password", "Mot de passe incorrect.")
        else:
            user = request.user
            user.is_active = False
            user.save(update_fields=["is_active"])
            user.listings.filter(status=Listing.Status.PUBLISHED).update(status=Listing.Status.INACTIVE)
            logout(request)
            messages.success(request, "Votre compte a été désactivé.")
            return redirect("listings:home")
    return render(request, "accounts/deactivate.html", {"form": form})


def public_profile(request, username):
    seller = get_object_or_404(User, username=username, is_active=True)
    listings = seller.listings.public().prefetch_related("images")
    page = Paginator(listings, 24).get_page(request.GET.get("page"))
    reviews = seller.reviews_received.filter(is_hidden=False).select_related("author").order_by("-created_at")[:20]
    return render(request, "accounts/public_profile.html", {
        "seller": seller, "page": page, "reviews": reviews, "rating": seller.rating_summary(),
    })


@login_required
@require_POST
def logout_view(request):
    logout(request)
    return redirect("listings:home")
