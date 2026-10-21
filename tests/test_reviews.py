from django.test import TestCase
from django.urls import reverse

from orders.models import CartItem, Order
from orders.services import change_status, checkout
from reviews.models import Review

from .helpers import DELIVERY, MediaMixin, make_listing, make_user


class ReviewTests(MediaMixin, TestCase):
    def setUp(self):
        self.seller = make_user("vendeur")
        self.buyer = make_user("acheteur")
        CartItem.objects.create(user=self.buyer, listing=make_listing(self.seller))
        self.order = checkout(self.buyer, DELIVERY)[0]
        self.url = reverse("reviews:create", args=[self.order.order_number])

    def _deliver(self):
        for s in [Order.Status.CONFIRMED, Order.Status.SHIPPED, Order.Status.DELIVERED]:
            self.order = change_status(self.order, s, self.seller)

    def test_review_requires_delivered_order(self):
        self.client.force_login(self.buyer)
        self.client.post(self.url, {"rating": 5})
        self.assertFalse(Review.objects.exists())

    def test_one_review_per_transaction(self):
        self._deliver()
        self.client.force_login(self.buyer)
        self.client.post(self.url, {"rating": 4, "comment": "Très bien"})
        self.client.post(self.url, {"rating": 1, "comment": "Encore"})
        self.assertEqual(Review.objects.count(), 1)
        review = Review.objects.get()
        self.assertEqual((review.seller, review.rating), (self.seller, 4))
        self.assertEqual(self.seller.rating_summary()["avg"], 4)

    def test_only_buyer_can_review(self):
        self._deliver()
        self.client.force_login(self.seller)
        self.assertEqual(self.client.post(self.url, {"rating": 5}).status_code, 404)

    def test_rating_bounds(self):
        self._deliver()
        self.client.force_login(self.buyer)
        self.client.post(self.url, {"rating": 9})
        self.assertFalse(Review.objects.exists())
