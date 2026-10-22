from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path, re_path
from django.views.static import serve
from django.views.generic import TemplateView

from listings.sitemaps import CategorySitemap, ListingSitemap

admin.site.site_header = f"{settings.SITE_NAME} — Administration"
admin.site.site_title = settings.SITE_NAME

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("", include("listings.urls")),
    path("compte/", include("accounts.urls")),
    path("favoris/", include("favorites.urls")),
    path("", include("orders.urls")),
    path("messages/", include("messaging.urls")),
    path("avis/", include("reviews.urls")),
    path("notifications/", include("notifications.urls")),
    path("moderation/", include("moderation.urls")),
    path("mentions-legales/", TemplateView.as_view(template_name="pages/legal.html"), name="legal"),
    path("conditions-utilisation/", TemplateView.as_view(template_name="pages/terms.html"), name="terms"),
    path("confidentialite/", TemplateView.as_view(template_name="pages/privacy.html"), name="privacy"),
    path("contact/", TemplateView.as_view(template_name="pages/contact.html"), name="contact"),
    path("sitemap.xml", sitemap, {"sitemaps": {"listings": ListingSitemap, "categories": CategorySitemap}},
         name="django.contrib.sitemaps.views.sitemap"),
    path("robots.txt", TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
elif settings.SERVE_MEDIA:
    urlpatterns += [re_path(rf"^{settings.MEDIA_URL.lstrip('/')}(?P<path>.*)$", serve,
                            {"document_root": settings.MEDIA_ROOT})]

handler404 = "config.views.not_found"
handler500 = "config.views.server_error"
