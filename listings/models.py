import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from .validators import validate_image_file


class Category(models.Model):
    name = models.CharField("nom", max_length=80)
    slug = models.SlugField(max_length=100, unique=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="children",
        verbose_name="catégorie parente",
    )
    icon = models.CharField("icône", max_length=40, blank=True, help_text="Nom d'icône Bootstrap, ex. bag")
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField("active", default=True)

    class Meta:
        verbose_name = "catégorie"
        ordering = ["position", "name"]

    def __str__(self):
        return f"{self.parent} › {self.name}" if self.parent_id else self.name

    def get_absolute_url(self):
        return reverse("listings:category", args=[self.slug])

    def descendant_ids(self):
        ids = [self.pk]
        for child in self.children.all():
            ids += child.descendant_ids()
        return ids


class ListingQuerySet(models.QuerySet):
    def public(self):
        """Annonces visibles dans le catalogue public."""
        return self.filter(
            status=Listing.Status.PUBLISHED,
            seller__is_active=True,
            seller__is_suspended=False,
        )

    def purchasable(self):
        return self.public().filter(quantity__gt=0)


class Listing(models.Model):
    class Condition(models.TextChoices):
        NEW = "new", "Neuf"
        VERY_GOOD = "very_good", "Très bon état"
        GOOD = "good", "Bon état"
        FAIR = "fair", "État satisfaisant"

    class Status(models.TextChoices):
        DRAFT = "draft", "Brouillon"
        PENDING = "pending", "En attente"
        PUBLISHED = "published", "Publiée"
        INACTIVE = "inactive", "Désactivée"
        SOLD = "sold", "Vendue"
        SUSPENDED = "suspended", "Suspendue"
        DELETED = "deleted", "Supprimée"

    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="listings",
                               verbose_name="vendeur")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="listings",
                                 verbose_name="catégorie")
    title = models.CharField("titre", max_length=120)
    slug = models.SlugField(max_length=140, blank=True)
    description = models.TextField("description", max_length=5000)
    brand = models.CharField("marque", max_length=80, blank=True)
    size = models.CharField("taille", max_length=30, blank=True)
    condition = models.CharField("état", max_length=12, choices=Condition.choices)
    price = models.PositiveIntegerField("prix (XOF)", validators=[MinValueValidator(0)])
    quantity = models.PositiveIntegerField("quantité", default=1)
    city = models.CharField("ville", max_length=80)
    commune = models.CharField("commune / quartier", max_length=80, blank=True)
    status = models.CharField("statut", max_length=12, choices=Status.choices, default=Status.PUBLISHED)
    views_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField("publiée le", auto_now_add=True)
    updated_at = models.DateTimeField("modifiée le", auto_now=True)

    objects = ListingQuerySet.as_manager()

    class Meta:
        verbose_name = "annonce"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["status", "price"]),
            models.Index(fields=["category", "status"]),
            models.Index(fields=["city"]),
            models.Index(fields=["brand"]),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(price__gte=0), name="listing_price_gte_0"),
            models.CheckConstraint(condition=models.Q(quantity__gte=0), name="listing_quantity_gte_0"),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.slug = slugify(self.title)[:140] or "article"
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("listings:detail", args=[self.pk, self.slug])

    @property
    def is_public(self):
        return (self.status == self.Status.PUBLISHED and self.seller.is_active
                and not self.seller.is_suspended)

    @property
    def is_purchasable(self):
        return self.is_public and self.quantity > 0

    @property
    def cover(self):
        imgs = list(self.images.all())
        return imgs[0] if imgs else None


def listing_image_path(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
    return f"listings/{uuid.uuid4().hex[:2]}/{uuid.uuid4().hex}.{ext}"


class ListingImage(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to=listing_image_path, validators=[validate_image_file])
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]
        verbose_name = "photo"
