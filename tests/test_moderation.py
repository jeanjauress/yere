import os
import sqlite3
import tempfile
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from listings.models import Listing
from moderation.models import AuditLog, Report

from .helpers import MediaMixin, make_listing, make_user


class ModerationTests(MediaMixin, TestCase):
    def setUp(self):
        self.seller = make_user("vendeur")
        self.listing = make_listing(self.seller)
        self.admin = make_user("modo", role="admin")
        self.user = make_user("membre")

    def test_admin_pages_forbidden_to_regular_users(self):
        self.client.force_login(self.user)
        for name in ["moderation:dashboard", "moderation:reports", "moderation:users", "moderation:audit"]:
            self.assertEqual(self.client.get(reverse(name)).status_code, 302, name)
        resp = self.client.post(reverse("moderation:listing_action", args=[self.listing.pk, "suspendre"]))
        self.assertEqual(resp.status_code, 302)
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.status, Listing.Status.PUBLISHED)

    def test_admin_dashboard(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("moderation:dashboard")).status_code, 200)

    def test_report_then_suspend_listing_is_logged(self):
        self.client.force_login(self.user)
        self.client.post(reverse("moderation:report_listing", args=[self.listing.pk]),
                         {"reason": "fraud", "details": "Prix trop bas"})
        report = Report.objects.get()
        self.assertEqual(report.reported_user, self.seller)
        self.client.force_login(self.admin)
        self.client.post(reverse("moderation:report_detail", args=[report.pk]),
                         {"action": "suspend_listing", "decision": "Arnaque avérée"})
        self.listing.refresh_from_db()
        report.refresh_from_db()
        self.assertEqual(self.listing.status, Listing.Status.SUSPENDED)
        self.assertEqual(report.status, Report.Status.RESOLVED)
        self.assertTrue(AuditLog.objects.filter(action="listing.suspend", actor=self.admin).exists())
        self.assertTrue(self.seller.notifications.filter(kind="moderation").exists())

    def test_suspend_user_is_logged_and_blocks_login(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("moderation:user_action", args=[self.seller.pk, "suspendre"]))
        self.seller.refresh_from_db()
        self.assertTrue(self.seller.is_suspended)
        self.assertTrue(AuditLog.objects.filter(action="user.suspend").exists())
        self.client.logout()
        self.assertFalse(self.client.login(username="vendeur", password="Motdepasse-123"))

    def test_suspended_owner_cannot_republish(self):
        self.listing.status = Listing.Status.SUSPENDED
        self.listing.save()
        self.client.force_login(self.seller)
        self.client.post(reverse("listings:change_status", args=[self.listing.pk, "activate"]))
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.status, Listing.Status.SUSPENDED)


class BackupRestoreTests(TestCase):
    def test_backup_and_restore_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "live.sqlite3"
            con = sqlite3.connect(db)
            con.execute("create table t (v text)")
            con.execute("insert into t values ('avant')")
            con.commit()
            con.close()
            with override_settings(SQLITE_PATH=db, BACKUP_DIR=Path(tmp) / "backups"):
                call_command("backup_db", stdout=open(os.devnull, "w"))
                backup = next((Path(tmp) / "backups").glob("db-*.sqlite3"))
                con = sqlite3.connect(db)
                con.execute("update t set v='après'")
                con.commit()
                con.close()
                call_command("restore_db", str(backup), "--yes", stdout=open(os.devnull, "w"))
            con = sqlite3.connect(db)
            self.assertEqual(con.execute("select v from t").fetchone()[0], "avant")
            con.close()
