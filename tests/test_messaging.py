from django.test import TestCase
from django.urls import reverse

from messaging.models import Block, Conversation, Message
from notifications.models import Notification

from .helpers import MediaMixin, make_listing, make_user


class MessagingTests(MediaMixin, TestCase):
    def setUp(self):
        self.seller = make_user("vendeur")
        self.buyer = make_user("acheteur")
        self.listing = make_listing(self.seller)

    def _start(self):
        self.client.force_login(self.buyer)
        resp = self.client.get(reverse("messaging:start", args=[self.listing.pk]))
        return Conversation.objects.get(), resp

    def test_conversation_linked_to_listing_and_reused(self):
        conv, resp = self._start()
        self.assertRedirects(resp, reverse("messaging:thread", args=[conv.pk]))
        self.assertEqual(conv.listing, self.listing)
        self.client.get(reverse("messaging:start", args=[self.listing.pk]))
        self.assertEqual(Conversation.objects.count(), 1)

    def test_send_read_and_notify(self):
        conv, _ = self._start()
        self.client.post(reverse("messaging:thread", args=[conv.pk]), {"body": "Toujours dispo ?"})
        msg = Message.objects.get()
        self.assertIsNone(msg.read_at)
        self.assertTrue(Notification.objects.filter(user=self.seller, kind="message").exists())
        self.assertEqual(Message.objects.unread_for(self.seller).count(), 1)
        self.client.force_login(self.seller)
        self.assertContains(self.client.get(reverse("messaging:thread", args=[conv.pk])), "Toujours dispo ?")
        msg.refresh_from_db()
        self.assertIsNotNone(msg.read_at)

    def test_outsider_cannot_read_conversation(self):
        conv, _ = self._start()
        self.client.post(reverse("messaging:thread", args=[conv.pk]), {"body": "secret"})
        self.client.force_login(make_user("intrus"))
        self.assertEqual(self.client.get(reverse("messaging:thread", args=[conv.pk])).status_code, 404)
        self.assertNotContains(self.client.get(reverse("messaging:inbox")), "secret")

    def test_block_prevents_messages(self):
        conv, _ = self._start()
        Block.objects.create(blocker=self.seller, blocked=self.buyer)
        self.client.post(reverse("messaging:thread", args=[conv.pk]), {"body": "Hello"})
        self.assertFalse(Message.objects.exists())

    def test_messages_are_escaped(self):
        conv, _ = self._start()
        self.client.post(reverse("messaging:thread", args=[conv.pk]), {"body": "<script>alert(1)</script>"})
        resp = self.client.get(reverse("messaging:thread", args=[conv.pk]))
        self.assertNotContains(resp, "<script>alert(1)</script>")
        self.assertContains(resp, "&lt;script&gt;")
