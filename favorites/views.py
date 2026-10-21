from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from listings.models import Listing

from .models import Favorite


@login_required
def favorite_list(request):
    qs = Favorite.objects.filter(user=request.user).select_related("listing__seller") \
        .prefetch_related("listing__images")
    page = Paginator(qs, 24).get_page(request.GET.get("page"))
    return render(request, "favorites/list.html", {"page": page})


@login_required
@require_POST
def toggle(request, pk):
    listing = get_object_or_404(Listing, pk=pk)
    existing = Favorite.objects.filter(user=request.user, listing=listing)
    if existing.exists():
        existing.delete()
        created = False
    elif listing.is_public:
        Favorite.objects.create(user=request.user, listing=listing)
        created = True
    else:
        raise Http404
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"favorite": created, "count": listing.favorited_by.count()})
    nxt = request.POST.get("next")
    if nxt and url_has_allowed_host_and_scheme(nxt, {request.get_host()}, request.is_secure()):
        return redirect(nxt)
    return redirect(listing)
