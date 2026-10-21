import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Avg, Count

from listings.validators import validate_image_file


def avatar_path(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
    return f"avatars/{uuid.uuid4().hex}.{ext}"


class User(AbstractUser):
    class Role(models.TextChoices):
        USER = "user", "Utilisateur"
        ADMIN = "admin", "Administrateur"

    email = models.EmailField("adresse e-mail", unique=True)
    phone = models.CharField("téléphone", max_length=20, blank=True)
    profile_image = models.ImageField(
        "photo de profil", upload_to=avatar_path, blank=True, validators=[validate_image_file]
    )
    bio = models.TextField("présentation", max_length=500, blank=True)
    city = models.CharField("ville", max_length=80, blank=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.USER)
    email_verified = models.BooleanField("e-mail vérifié", default=False)
    is_suspended = models.BooleanField("suspendu", default=False)

    class Meta:
        verbose_name = "utilisateur"

    def __str__(self):
        return self.username

    @property
    def is_platform_admin(self):
        return self.is_superuser or self.role == self.Role.ADMIN

    def rating_summary(self):
        return self.reviews_received.filter(is_hidden=False).aggregate(avg=Avg("rating"), count=Count("id"))

    def save(self, *args, **kwargs):
        if self.role == self.Role.ADMIN:
            self.is_staff = True
        super().save(*args, **kwargs)
