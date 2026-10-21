import threading

from django.db import connection
from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from listings.models import Listing
from notifications.models import Notification
from orders.models import CartItem, Order, Payment
from orders.services import CheckoutError, change_status, checkout

from .helpers import DELIVERY, MediaMixin, make_listing, make_user


class CartAndCheckoutTests(MediaMixin, TestCase):
    def setUp(self):
        self.seller = make_user("vendeur")
        self.seller2 = make_user("vendeur2")
        self.buyer = make_user("acheteur")
        self.listing = make_listing(self.seller, price=10000, quantity=3)

    def test_add_to_cart_caps_quantity_to_stock(self):
        self.client.force_login(self.buyer)
        self.client.post(reverse("orders:cart_add", args=[self.listing.pk]), {"quantity": 10})
        self.assertEqual(CartItem.objects.get().quantity, 3)

    def test_cannot_buy_own_listing(self):
        self.client.force_login(self.seller)
        self.client.post(reverse("orders:cart_add", args=[self.listing.pk]))
        self.assertFalse(CartItem.objects.exists())
        CartItem.objects.create(user=self.seller, listing=self.listing)
        with self.assertRaises(CheckoutError):
            checkout(self.seller, DELIVERY)

    def test_checkout_flow_server_side_amounts(self):
        other = make_listing(self.seller2, price=5000, quantity=1, title="Montre")
        self.client.force_login(self.buyer)
        self.client.post(reverse("orders:cart_add", args=[self.listing.pk]), {"quantity": 2})
        self.client.post(reverse("orders:cart_add", args=[other.pk]))
        # Un montant envoyé par le navigateur est ignoré.
        resp = self.client.post(reverse("orders:checkout"), {**DELIVERY, "total_amount": 1})
        self.assertRedirects(resp, reverse("orders:purchases"))
        orders = Order.objects.order_by("total_amount")
        self.assertEqual(orders.count(), 2)  # une commande par vendeur
        self.assertEqual(orders[0].total_amount, 5000 + 1500)
        self.assertEqual(orders[1].total_amount, 20000 + 1500)
        self.assertEqual(orders[1].items.get().unit_price, 10000)
        self.listing.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(self.listing.quantity, 1)
        self.assertEqual(other.quantity, 0)
        self.assertEqual(other.status, Listing.Status.SOLD)
        self.assertFalse(CartItem.objects.exists())
        self.assertEqual(Payment.objects.filter(provider="cod").count(), 2)
        self.assertTrue(Notification.objects.filter(user=self.seller, kind="order_received").exists())
        self.assertTrue(Notification.objects.filter(user=self.seller2, kind="item_sold").exists())

    def test_price_snapshot_kept_after_listing_change(self):
        CartItem.objects.create(user=self.buyer, listing=self.listing)
        order = checkout(self.buyer, DELIVERY)[0]
        Listing.objects.filter(pk=self.listing.pk).update(price=99999, title="Autre titre")
        item = order.items.get()
        self.assertEqual((item.unit_price, item.title), (10000, "Robe wax"))

    def test_second_buyer_cannot_buy_sold_out_item(self):
        unique = make_listing(self.seller, quantity=1, title="Pièce unique")
        buyer2 = make_user("acheteur2")
        CartItem.objects.create(user=self.buyer, listing=unique)
        CartItem.objects.create(user=buyer2, listing=unique)
        checkout(self.buyer, DELIVERY)
        with self.assertRaises(CheckoutError):
            checkout(buyer2, DELIVERY)
        unique.refresh_from_db()
        self.assertEqual(unique.quantity, 0)
        self.assertEqual(Order.objects.filter(buyer=buyer2).count(), 0)

    def test_failed_checkout_rolls_back_everything(self):
        """Si un article du panier n'est plus disponible, aucune commande n'est créée et aucun stock n'est pris."""
        ok = make_listing(self.seller2, quantity=2, title="OK")
        gone = make_listing(self.seller, quantity=1, title="Parti")
        CartItem.objects.create(user=self.buyer, listing=ok)
        CartItem.objects.create(user=self.buyer, listing=gone, quantity=1)
        Listing.objects.filter(pk=gone.pk).update(quantity=0)  # acheté entre-temps
        with self.assertRaises(CheckoutError):
            checkout(self.buyer, DELIVERY)
        ok.refresh_from_db()
        self.assertEqual(ok.quantity, 2)
        self.assertFalse(Order.objects.exists())
        self.assertEqual(CartItem.objects.filter(user=self.buyer).count(), 2)

    def test_status_flow_and_cancel_restores_stock(self):
        CartItem.objects.create(user=self.buyer, listing=self.listing, quantity=3)
        order = checkout(self.buyer, DELIVERY)[0]
        self.listing.refresh_from_db()
        self.assertEqual((self.listing.quantity, self.listing.status), (0, "sold"))
        self.client.force_login(self.buyer)
        self.client.post(reverse("orders:buyer_action", args=[order.order_number, "annuler"]))
        order.refresh_from_db()
        self.listing.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CANCELLED)
        self.assertEqual((self.listing.quantity, self.listing.status), (3, "published"))

    def test_seller_updates_and_cod_paid_on_delivery(self):
        CartItem.objects.create(user=self.buyer, listing=self.listing)
        order = checkout(self.buyer, DELIVERY)[0]
        self.client.force_login(self.seller)
        url = reverse("orders:seller_update", args=[order.order_number])
        for status in ["confirmed", "preparing", "shipped"]:
            self.client.post(url, {"status": status, "tracking_note": "Livreur Yango"})
            order.refresh_from_db()
            self.assertEqual(order.status, status)
        # Le vendeur ne peut pas sauter d'étape ni rembourser.
        self.client.post(url, {"status": "refunded"})
        order.refresh_from_db()
        self.assertEqual(order.status, "shipped")
        self.client.force_login(self.buyer)
        self.client.post(reverse("orders:buyer_action", args=[order.order_number, "recue"]))
        order.refresh_from_db()
        self.assertEqual(order.status, "delivered")
        self.assertEqual(order.payment_status, "paid")
        self.assertTrue(Notification.objects.filter(user=self.buyer, kind="order_status").exists())

    def test_invalid_transition_rejected(self):
        CartItem.objects.create(user=self.buyer, listing=self.listing)
        order = checkout(self.buyer, DELIVERY)[0]
        with self.assertRaises(CheckoutError):
            change_status(order, Order.Status.DELIVERED, self.seller)

    def test_buyer_cannot_cancel_after_confirmation(self):
        CartItem.objects.create(user=self.buyer, listing=self.listing)
        order = checkout(self.buyer, DELIVERY)[0]
        change_status(order, Order.Status.CONFIRMED, self.seller)
        self.client.force_login(self.buyer)
        self.client.post(reverse("orders:buyer_action", args=[order.order_number, "annuler"]))
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CONFIRMED)

    def test_order_access_control(self):
        CartItem.objects.create(user=self.buyer, listing=self.listing)
        order = checkout(self.buyer, DELIVERY)[0]
        self.client.force_login(make_user("curieux"))
        self.assertEqual(self.client.get(order.get_absolute_url()).status_code, 404)
        self.client.force_login(self.buyer)
        self.assertEqual(self.client.post(reverse("orders:seller_update", args=[order.order_number]),
                                          {"status": "confirmed"}).status_code, 404)


class ConcurrentCheckoutTests(MediaMixin, TransactionTestCase):
    """Plusieurs acheteurs valident en même temps le dernier exemplaire : une seule vente."""

    def test_simultaneous_purchases_sell_only_once(self):
        seller = make_user("vendeur")
        listing = make_listing(seller, quantity=1, title="Dernier exemplaire")
        buyers = [make_user(f"acheteur{i}") for i in range(6)]
        for b in buyers:
            CartItem.objects.create(user=b, listing=listing)
        results = []
        barrier = threading.Barrier(len(buyers))

        def buy(user):
            try:
                barrier.wait()
                checkout(user, DELIVERY)
                results.append("ok")
            except CheckoutError:
                results.append("refusé")
            finally:
                connection.close()

        threads = [threading.Thread(target=buy, args=(b,)) for b in buyers]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        listing.refresh_from_db()
        self.assertEqual(results.count("ok"), 1, results)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(listing.quantity, 0)
