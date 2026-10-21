from django.core import mail
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from accounts import tokens

from .helpers import User, make_user


class SignupLoginTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_signup_hashes_password_and_sends_verification(self):
        resp = self.client.post(reverse("accounts:signup"), {
            "username": "koffi", "email": "Koffi@Test.ci", "phone": "0700000000",
            "password1": "Un-motdepasse-solide-9", "password2": "Un-motdepasse-solide-9", "accept_terms": "on",
        })
        self.assertRedirects(resp, reverse("accounts:dashboard"))
        user = User.objects.get(username="koffi")
        self.assertEqual(user.email, "koffi@test.ci")
        self.assertNotEqual(user.password, "Un-motdepasse-solide-9")
        self.assertTrue(user.password.startswith(("pbkdf2_", "argon2", "bcrypt")))
        self.assertFalse(user.email_verified)
        self.assertEqual(len(mail.outbox), 1)

    def test_duplicate_email_rejected(self):
        make_user("a", email="dup@test.ci")
        resp = self.client.post(reverse("accounts:signup"), {
            "username": "b", "email": "DUP@test.ci", "password1": "Un-motdepasse-solide-9",
            "password2": "Un-motdepasse-solide-9", "accept_terms": "on"})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(User.objects.filter(username="b").exists())

    def test_email_verification(self):
        user = make_user()
        resp = self.client.get(reverse("accounts:verify_email", args=[tokens.make_token(user)]))
        self.assertEqual(resp.status_code, 302)
        user.refresh_from_db()
        self.assertTrue(user.email_verified)
        resp = self.client.get(reverse("accounts:verify_email", args=["faux-jeton"]))
        self.assertEqual(resp.status_code, 302)

    def test_login_with_email_or_username(self):
        make_user("alice", password="Motdepasse-123")
        for ident in ("alice", "alice@test.ci"):
            self.client.logout()
            resp = self.client.post(reverse("accounts:login"), {"username": ident, "password": "Motdepasse-123"})
            self.assertRedirects(resp, reverse("accounts:dashboard"), msg_prefix=ident)

    def test_login_rate_limited(self):
        make_user("alice", password="Motdepasse-123")
        url = reverse("accounts:login")
        for _ in range(5):
            self.client.post(url, {"username": "alice", "password": "faux"})
        resp = self.client.post(url, {"username": "alice", "password": "Motdepasse-123"})
        self.assertEqual(resp.status_code, 200)  # bloqué malgré le bon mot de passe
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_protected_pages_require_login(self):
        for name in ["accounts:dashboard", "accounts:settings", "listings:create", "orders:cart",
                     "favorites:list", "messaging:inbox", "notifications:list"]:
            resp = self.client.get(reverse(name))
            self.assertEqual(resp.status_code, 302, name)
            self.assertIn(reverse("accounts:login"), resp.url)

    def test_password_reset_sends_mail(self):
        make_user("alice")
        self.client.post(reverse("accounts:password_reset"), {"email": "alice@test.ci"})
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/compte/mot-de-passe/reinitialiser/", mail.outbox[0].body)

    def test_deactivate_account(self):
        user = make_user("alice", password="Motdepasse-123")
        self.client.force_login(user)
        resp = self.client.post(reverse("accounts:deactivate"), {"password": "Motdepasse-123", "confirm": "on"})
        self.assertEqual(resp.status_code, 302)
        user.refresh_from_db()
        self.assertFalse(user.is_active)

    def test_suspended_user_is_logged_out(self):
        user = make_user()
        self.client.force_login(user)
        User.objects.filter(pk=user.pk).update(is_suspended=True)
        resp = self.client.get(reverse("accounts:dashboard"))
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.url.startswith(reverse("accounts:login")))
        self.assertNotIn("_auth_user_id", self.client.session)
