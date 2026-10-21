from django.conf import settings
from django.db import models
from django.db.models import Q


class Conversation(models.Model):
    listing = models.ForeignKey("listings.Listing", on_delete=models.SET_NULL, null=True, blank=True,
                                related_name="conversations")
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="buyer_conversations")
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name="seller_conversations")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(fields=["listing", "buyer", "seller"], name="unique_conversation"),
        ]

    def __str__(self):
        return f"{self.buyer} ↔ {self.seller}"

    @classmethod
    def for_user(cls, user):
        return cls.objects.filter(Q(buyer=user) | Q(seller=user))

    def other(self, user):
        return self.seller if user.pk == self.buyer_id else self.buyer

    def has_participant(self, user):
        return user.pk in (self.buyer_id, self.seller_id)


class MessageQuerySet(models.QuerySet):
    def unread_for(self, user):
        return self.filter(Q(conversation__buyer=user) | Q(conversation__seller=user), read_at__isnull=True) \
            .exclude(sender=user)


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages")
    body = models.TextField("message", max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    objects = MessageQuerySet.as_manager()

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["conversation", "created_at"])]


class Block(models.Model):
    blocker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blocks")
    blocked = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blocked_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "blocage"
        constraints = [models.UniqueConstraint(fields=["blocker", "blocked"], name="unique_block")]

    @classmethod
    def between(cls, a, b):
        return cls.objects.filter(Q(blocker=a, blocked=b) | Q(blocker=b, blocked=a)).exists()
