from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, F, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from favorites.models import Favorite

from .forms import ListingForm, SearchForm
from .models import Category, Listing, ListingImage

PAGE_SIZE = 24


def home(request):
    public = Listing.objects.public().select_related("seller").prefetch_related("images")
    ctx = {
        "categories": Category.objects.filter(is_active=True, parent__isnull=True),
        "recent": public[:12],
        "popular": public.annotate(fav=Count("favorited_by")).order_by("-fav", "-views_count")[:8],
    }
    if request.user.is_authenticated:
        fav_cats = Favorite.objects.filter(user=request.user).values_list("listing__category", flat=True)
        ctx["recommended"] = public.filter(category__in=fav_cats).exclude(seller=request.user) \
            .exclude(favorited_by__user=request.user)[:8]
    return render(request, "listings/home.html", ctx)


def search(request, slug=None):
    data = request.GET.copy()
    category = None
    if slug:
        category = get_object_or_404(Category, slug=slug, is_active=True)
        data["category"] = slug
    form = SearchForm(data)
    qs = Listing.objects.public().select_related("seller", "category").prefetch_related("images")
    if form.is_valid():
        d = form.cleaned_data
        if d["q"]:
            for word in d["q"].split()[:6]:
                qs = qs.filter(Q(title__icontains=word) | Q(description__icontains=word) | Q(brand__icontains=word))
        if d["category"]:
            category = d["category"]
            qs = qs.filter(category_id__in=category.descendant_ids())
        if d["min_price"] is not None:
            qs = qs.filter(price__gte=d["min_price"])
        if d["max_price"] is not None:
            qs = qs.filter(price__lte=d["max_price"])
        if d["condition"]:
            qs = qs.filter(condition=d["condition"])
        if d["brand"]:
            qs = qs.filter(brand__icontains=d["brand"])
        if d["city"]:
            qs = qs.filter(Q(city__icontains=d["city"]) | Q(commune__icontains=d["city"]))
        qs = qs.order_by({
            "price_asc": "price", "price_desc": "-price", "popular": "-views_count",
        }.get(d["sort"], "-created_at"), "-id")
    page = Paginator(qs, PAGE_SIZE).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "listings/search.html", {
        "form": form, "page": page, "category": category, "querystring": params.urlencode(),
        "categories": Category.objects.filter(is_active=True, parent__isnull=True).prefetch_related("children"),
    })


def detail(request, pk, slug=None):
    listing = get_object_or_404(Listing.objects.select_related("seller", "category__parent"), pk=pk)
    is_owner = request.user.is_authenticated and request.user == listing.seller
    is_staff = request.user.is_authenticated and request.user.is_staff
    if not listing.is_public and listing.status != Listing.Status.SOLD and not (is_owner or is_staff):
        raise Http404
    if listing.status == Listing.Status.DELETED and not is_staff:
        raise Http404
    if slug != listing.slug:
        return redirect(listing, permanent=True)
    if not is_owner:
        Listing.objects.filter(pk=pk).update(views_count=F("views_count") + 1)
    is_favorite = request.user.is_authenticated and Favorite.objects.filter(
        user=request.user, listing=listing).exists()
    similar = Listing.objects.public().filter(category=listing.category).exclude(pk=pk) \
        .prefetch_related("images")[:4]
    return render(request, "listings/detail.html", {
        "listing": listing, "is_owner": is_owner, "is_favorite": is_favorite, "similar": similar,
        "rating": listing.seller.rating_summary(),
    })


def _save_photos(listing, photos):
    start = listing.images.count()
    for i, f in enumerate(photos):
        ListingImage.objects.create(listing=listing, image=f, position=start + i)


@login_required
def create(request):
    form = ListingForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            listing = form.save(commit=False)
            listing.seller = request.user
            listing.status = Listing.Status.DRAFT if form.cleaned_data["save_as_draft"] else Listing.Status.PUBLISHED
            listing.save()
            _save_photos(listing, form.cleaned_data["photos"])
        messages.success(request, "Annonce enregistrée." if listing.status == Listing.Status.DRAFT
                         else "Votre annonce est en ligne !")
        return redirect(listing)
    return render(request, "listings/form.html", {"form": form, "title": "Déposer un article"})


def _own_listing(request, pk):
    return get_object_or_404(Listing.objects.exclude(status=Listing.Status.DELETED), pk=pk, seller=request.user)


@login_required
def edit(request, pk):
    listing = _own_listing(request, pk)
    if listing.status == Listing.Status.SUSPENDED:
        messages.error(request, "Cette annonce est suspendue par la modération et ne peut pas être modifiée.")
        return redirect("listings:mine")
    form = ListingForm(request.POST or None, request.FILES or None, instance=listing,
                       initial={"save_as_draft": listing.status == Listing.Status.DRAFT})
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            listing = form.save(commit=False)
            if form.cleaned_data["save_as_draft"]:
                listing.status = Listing.Status.DRAFT
            elif listing.status in (Listing.Status.DRAFT, Listing.Status.SOLD) and listing.quantity > 0:
                listing.status = Listing.Status.PUBLISHED
            listing.save()
            remove = request.POST.getlist("remove_image")
            listing.images.filter(pk__in=[r for r in remove if r.isdigit()]).delete()
            _save_photos(listing, form.cleaned_data["photos"])
        messages.success(request, "Annonce mise à jour.")
        return redirect(listing)
    return render(request, "listings/form.html", {"form": form, "listing": listing, "title": "Modifier l'annonce"})


@login_required
@require_POST
def change_status(request, pk, action):
    listing = _own_listing(request, pk)
    S = Listing.Status
    if listing.status == S.SUSPENDED:
        messages.error(request, "Annonce suspendue par la modération.")
        return redirect("listings:mine")
    transitions = {
        "deactivate": ({S.PUBLISHED}, S.INACTIVE, "Annonce désactivée."),
        "activate": ({S.INACTIVE, S.DRAFT}, S.PUBLISHED, "Annonce publiée."),
        "sold": ({S.PUBLISHED, S.INACTIVE}, S.SOLD, "Annonce marquée comme vendue."),
        "delete": ({S.DRAFT, S.PUBLISHED, S.INACTIVE, S.SOLD, S.PENDING}, S.DELETED, "Annonce supprimée."),
    }
    if action not in transitions:
        raise Http404
    allowed, target, msg = transitions[action]
    if listing.status not in allowed:
        messages.error(request, "Action impossible pour ce statut.")
    elif target == S.PUBLISHED and (listing.quantity == 0 or not listing.images.exists()):
        messages.error(request, "Ajoutez une photo et une quantité disponible avant de publier.")
    else:
        listing.status = target
        listing.save(update_fields=["status", "updated_at"])
        if target in (S.DELETED, S.SOLD, S.INACTIVE):
            from orders.models import CartItem
            CartItem.objects.filter(listing=listing).delete()
        messages.success(request, msg)
    return redirect("listings:mine")


@login_required
def mine(request):
    status = request.GET.get("statut", "")
    qs = request.user.listings.exclude(status=Listing.Status.DELETED).prefetch_related("images")
    if status in Listing.Status.values:
        qs = qs.filter(status=status)
    page = Paginator(qs, 20).get_page(request.GET.get("page"))
    return render(request, "listings/mine.html", {
        "page": page, "status": status,
        "statuses": [s for s in Listing.Status.choices if s[0] != Listing.Status.DELETED],
    })
