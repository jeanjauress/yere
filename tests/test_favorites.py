from django.test import TestCase
from django.urls import reverse

from favorites.models import Favorite

from .helpers import MediaMixin, make_listing, make_user


class FavoriteTests(MediaMixin, TestCase):
    def test_toggle_and_uniqueness(self):
        listing = make_listing(make_user("vendeur"))
        buyer = make_user("acheteur")
        self.client.force_login(buyer)
        url = reverse("favorites:toggle", args=[listing.pk])
        self.client.post(url)
        self.assertEqual(Favorite.objects.filter(user=buyer, listing=listing).count(), 1)
        self.assertContains(self.client.get(reverse("favorites:list")), listing.title)
        self.client.post(url)
        self.assertFalse(Favorite.objects.exists())

    def test_db_unique_constraint(self):
        from django.db import IntegrityError, transaction
        listing = make_listing(make_user("vendeur"))
        buyer = make_user("acheteur")
        Favorite.objects.create(user=buyer, listing=listing)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Favorite.objects.create(user=buyer, listing=listing)
