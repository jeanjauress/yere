import io
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image

from listings.models import Category, Listing, ListingImage

User = get_user_model()
TEMP_MEDIA = tempfile.mkdtemp(prefix="test-media-")


def image_file(name="photo.jpg", fmt="JPEG", size=(60, 80)):
    buf = io.BytesIO()
    Image.new("RGB", size, "green").save(buf, fmt)
    return SimpleUploadedFile(name, buf.getvalue(), content_type=f"image/{fmt.lower()}")


def make_user(username="alice", password="Motdepasse-123", **kw):
    kw.setdefault("email", f"{username}@test.ci")
    return User.objects.create_user(username=username, password=password, **kw)


def make_category(name="Mode", parent=None):
    from django.utils.text import slugify
    return Category.objects.create(name=name, slug=slugify(name), parent=parent)


def make_listing(seller, category=None, with_image=True, **kw):
    category = category or Category.objects.first() or make_category()
    data = dict(title="Robe wax", description="Belle robe", condition="good", price=10000, quantity=1,
                city="Abidjan")
    data.update(kw)
    listing = Listing.objects.create(seller=seller, category=category, **data)
    if with_image:
        ListingImage.objects.create(listing=listing, image=image_file())
    return listing


class MediaMixin:
    @classmethod
    def setUpClass(cls):
        cls._media = override_settings(MEDIA_ROOT=TEMP_MEDIA)
        cls._media.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._media.disable()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)


DELIVERY = {
    "recipient_name": "Awa K.", "recipient_phone": "+225 0700000000", "delivery_address": "Rue des jardins",
    "commune": "Cocody", "city": "Abidjan", "delivery_mode": "abidjan", "payment_method": "cod",
}
