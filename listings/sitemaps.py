from django.contrib.sitemaps import Sitemap

from .models import Category, Listing


class ListingSitemap(Sitemap):
    changefreq = "daily"

    def items(self):
        return Listing.objects.public()[:5000]

    def lastmod(self, obj):
        return obj.updated_at


class CategorySitemap(Sitemap):
    def items(self):
        return Category.objects.filter(is_active=True)
