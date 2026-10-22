from django.conf import settings
from django.db import models


class Report(models.Model):
    class Reason(models.TextChoices):
        FRAUD = "fraud", "Arnaque / fraude"
        FORBIDDEN = "forbidden", "Article interdit"
        COUNTERFEIT = "counterfeit", "Contrefaçon"
        INAPPROPRIATE = "inappropriate", "Contenu inapproprié"
        HARASSMENT = "harassment", "Harcèlement / comportement abusif"
        SPAM = "spam", "Spam"
        OTHER = "other", "Autre"

    class Status(models.TextChoices):
        OPEN = "open", "À traiter"
        RESOLVED = "resolved", "Traité — mesure prise"
        DISMISSED = "dismissed", "Classé sans suite"

    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                 related_name="reports_made")
    listing = models.ForeignKey("listings.Listing", on_delete=models.CASCADE, null=True, blank=True,
                                related_name="reports")
    reported_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True,
                                      related_name="reports_received")
    reason = models.CharField("motif", max_length=20, choices=Reason.choices)
    details = models.TextField("précisions", max_length=1000, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    decision = models.TextField("décision", blank=True)
    handled_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="reports_handled")
    handled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "signalement"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "-created_at"])]

    URGENT_REASONS = {Reason.FRAUD, Reason.FORBIDDEN, Reason.COUNTERFEIT}
    MINOR_REASONS = {Reason.SPAM, Reason.OTHER}

    @property
    def severity(self):
        """(classe CSS, libellé) indiquant la priorité de traitement, d'après le motif."""
        if self.reason in self.URGENT_REASONS:
            return "bad", "Urgent"
        if self.reason in self.MINOR_REASONS:
            return "ok", "Mineur"
        return "warn", "À voir"


class AuditLog(models.Model):
    """Journal des actions sensibles (append-only)."""
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                              related_name="audit_entries")
    action = models.CharField(max_length=60)
    target_type = models.CharField(max_length=60)
    target_id = models.CharField(max_length=40)
    target_repr = models.CharField(max_length=200)
    details = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "journal d'audit"
        verbose_name_plural = "journal d'audit"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["action"]), models.Index(fields=["-created_at"])]
