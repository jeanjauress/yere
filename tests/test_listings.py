from django.test import TestCase
from django.urls import reverse

from listings.models import Listing

from .helpers import MediaMixin, image_file, make_category, make_listing, make_user


class ListingTests(MediaMixin, TestCase):
    def setUp(self):
        self.cat = make_category("Mode")
        self.sub = make_category("Robes", parent=self.cat)
        self.seller = make_user("vendeur")
        self.other = make_user("autre")

    def _post_data(self, **kw):
        data = {"title": "Robe wax", "category": self.sub.pk, "description": "Belle robe", "condition": "good",
                "price": 8500, "quantity": 1, "city": "Abidjan", "photos": [image_file()]}
        data.update(kw)
        return data

    def test_create_listing(self):
        self.client.force_login(self.seller)
        resp = self.client.post(reverse("listings:create"), self._post_data())
        listing = Listing.objects.get()
        self.assertRedirects(resp, listing.get_absolute_url())
        self.assertEqual(listing.seller, self.seller)
        self.assertEqual(listing.status, Listing.Status.PUBLISHED)
        self.assertEqual(listing.images.count(), 1)

    def test_rejects_fake_image_and_negative_values(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.client.force_login(self.seller)
        fake = SimpleUploadedFile("x.jpg", b"<?php echo 1; ?>", content_type="image/jpeg")
        resp = self.client.post(reverse("listings:create"), self._post_data(photos=[fake]))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.post(reverse("listings:create"), self._post_data(price=-5, quantity=-1))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Listing.objects.exists())

    def test_rejects_gif_format(self):
        self.client.force_login(self.seller)
        resp = self.client.post(reverse("listings:create"), self._post_data(photos=[image_file("a.gif", "GIF")]))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Listing.objects.exists())

    def test_only_owner_can_edit(self):
        listing = make_listing(self.seller, self.sub)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse("listings:edit", args=[listing.pk])).status_code, 404)
        resp = self.client.post(reverse("listings:change_status", args=[listing.pk, "delete"]))
        self.assertEqual(resp.status_code, 404)
        listing.refresh_from_db()
        self.assertEqual(listing.status, Listing.Status.PUBLISHED)

    def test_owner_status_changes(self):
        listing = make_listing(self.seller, self.sub)
        self.client.force_login(self.seller)
        for action, expected in [("deactivate", "inactive"), ("activate", "published"), ("sold", "sold"),
                                 ("delete", "deleted")]:
            self.client.post(reverse("listings:change_status", args=[listing.pk, action]))
            listing.refresh_from_db()
            self.assertEqual(listing.status, expected, action)

    def test_suspended_listing_hidden_from_public(self):
        listing = make_listing(self.seller, self.sub, title="Objet suspendu")
        listing.status = Listing.Status.SUSPENDED
        listing.save()
        self.assertNotContains(self.client.get(reverse("listings:search")), "Objet suspendu")
        self.assertEqual(self.client.get(listing.get_absolute_url()).status_code, 404)

    def test_suspended_seller_listings_hidden(self):
        make_listing(self.seller, self.sub, title="Objet vendeur suspendu")
        self.seller.is_suspended = True
        self.seller.save()
        self.assertNotContains(self.client.get(reverse("listings:search")), "Objet vendeur suspendu")

    def test_search_filters_and_sort(self):
        make_listing(self.seller, self.sub, title="iPhone 11", brand="Apple", price=150000, city="Abidjan")
        make_listing(self.seller, self.sub, title="Samsung A14", brand="Samsung", price=70000, city="Bouaké")
        make_listing(self.seller, self.sub, title="iPhone 8", brand="Apple", price=60000, condition="fair")
        url = reverse("listings:search")

        def titles(**params):
            return [l.title for l in self.client.get(url, params).context["page"]]

        self.assertEqual(set(titles(q="iphone")), {"iPhone 11", "iPhone 8"})
        self.assertEqual(titles(min_price=65000, max_price=100000), ["Samsung A14"])
        self.assertEqual(titles(city="bouak"), ["Samsung A14"])
        self.assertEqual(titles(condition="fair"), ["iPhone 8"])
        self.assertEqual(titles(brand="apple", sort="price_asc"), ["iPhone 8", "iPhone 11"])
        self.assertEqual(titles(sort="price_desc")[0], "iPhone 11")
        # La catégorie parente inclut les sous-catégories.
        resp = self.client.get(reverse("listings:category", args=[self.cat.slug]))
        self.assertEqual(resp.context["page"].paginator.count, 3)

    def test_pagination(self):
        for i in range(30):
            make_listing(self.seller, self.sub, title=f"Article {i}", with_image=False)
        resp = self.client.get(reverse("listings:search"))
        self.assertEqual(len(resp.context["page"]), 24)
        self.assertEqual(len(self.client.get(reverse("listings:search"), {"page": 2}).context["page"]), 6)

    def test_home_page(self):
        make_listing(self.seller, self.sub, title="Visible accueil")
        self.assertContains(self.client.get("/"), "Visible accueil")

    def test_price_display_xof(self):
        listing = make_listing(self.seller, self.sub, price=12500)
        self.assertContains(self.client.get(listing.get_absolute_url()), "12 500 FCFA")
