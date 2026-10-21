import io
import random
import unicodedata

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify
from PIL import Image, ImageDraw, ImageFont

from listings.models import Category, Listing, ListingImage

CATEGORIES = {
    ("Femmes", "handbag"): ["Robes", "Pagnes et tissus", "Chaussures femme", "Sacs", "Bijoux"],
    ("Hommes", "person"): ["Chemises", "Pantalons", "Chaussures homme", "Montres"],
    ("Enfants", "balloon"): ["Vêtements enfant", "Jouets", "Puériculture"],
    ("Électronique", "phone"): ["Téléphones", "Ordinateurs", "Audio", "Accessoires"],
    ("Maison", "house"): ["Meubles", "Électroménager", "Décoration", "Cuisine"],
    ("Beauté", "stars"): ["Parfums", "Soins", "Maquillage"],
    ("Sport et loisirs", "bicycle"): ["Vélos", "Fitness", "Livres"],
}

DEMO_ITEMS = [
    ("Robe en wax taille M", "Robes", "", 8500), ("Pagne Vlisco 6 yards", "Pagnes et tissus", "Vlisco", 25000),
    ("Escarpins noirs pointure 39", "Chaussures femme", "", 7000), ("Sac à main cuir marron", "Sacs", "", 12000),
    ("Chemise lin blanche L", "Chemises", "Zara", 6000), ("Jean slim bleu 32", "Pantalons", "Levi's", 9000),
    ("Baskets Nike Air Max 42", "Chaussures homme", "Nike", 35000), ("Montre Casio vintage", "Montres", "Casio", 15000),
    ("iPhone 11 64 Go", "Téléphones", "Apple", 160000), ("Samsung Galaxy A14", "Téléphones", "Samsung", 70000),
    ("Ordinateur portable HP 15\"", "Ordinateurs", "HP", 180000), ("Enceinte JBL Flip 5", "Audio", "JBL", 40000),
    ("Ventilateur sur pied", "Électroménager", "Binatone", 14000), ("Canapé 3 places", "Meubles", "", 120000),
    ("Lot de jouets éducatifs", "Jouets", "", 5000), ("Poussette pliable", "Puériculture", "", 30000),
    ("Parfum 100 ml neuf", "Parfums", "", 18000), ("Vélo VTT 26 pouces", "Vélos", "", 65000),
    ("Haltères 2 x 5 kg", "Fitness", "", 10000), ("Lot de romans africains", "Livres", "", 4000),
]
CITIES = [("Abidjan", "Cocody"), ("Abidjan", "Yopougon"), ("Abidjan", "Marcory"), ("Abidjan", "Plateau"),
          ("Bouaké", ""), ("Yamoussoukro", ""), ("San-Pédro", ""), ("Abidjan", "Treichville")]
COLORS = ["#0e8a6d", "#f08c00", "#5f3dc4", "#c92a2a", "#1971c2", "#2b8a3e", "#e8590c", "#495057"]


def placeholder_image(text, color):
    img = Image.new("RGB", (600, 800), color)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 44)
    except OSError:
        font = ImageFont.load_default(size=44)
        text = "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))
    lines = "\n".join(text[i:i + 18] for i in range(0, len(text), 18))
    draw.multiline_text((300, 400), lines, fill="white", font=font, anchor="mm", align="center")
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=80)
    return ContentFile(buf.getvalue(), name="demo.jpg")


class Command(BaseCommand):
    help = "Crée les catégories et, avec --demo, des comptes et annonces de démonstration."

    def add_arguments(self, parser):
        parser.add_argument("--demo", action="store_true", help="Ajoute aussi des utilisateurs et annonces fictifs.")

    @transaction.atomic
    def handle(self, *args, **opts):
        subs = {}
        for pos, ((name, icon), children) in enumerate(CATEGORIES.items()):
            parent, _ = Category.objects.get_or_create(slug=slugify(name), defaults={"name": name, "icon": icon,
                                                                                     "position": pos})
            for i, child in enumerate(children):
                subs[child], _ = Category.objects.get_or_create(
                    slug=slugify(child), defaults={"name": child, "parent": parent, "position": i})
        self.stdout.write(self.style.SUCCESS(f"{Category.objects.count()} catégories."))
        if not opts["demo"]:
            return

        User = get_user_model()
        sellers = []
        for name in ["awa", "kouadio", "fatou", "yao"]:
            u, created = User.objects.get_or_create(username=name, defaults={
                "email": f"{name}@demo.ci", "email_verified": True, "city": "Abidjan", "phone": "+225 07 00 00 00 00"})
            if created:
                u.set_password("demo12345!")
                u.save()
            sellers.append(u)
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", "admin@demo.ci", "admin12345!", role="admin", email_verified=True)

        rnd = random.Random(42)
        for i, (title, sub, brand, price) in enumerate(DEMO_ITEMS):
            if Listing.objects.filter(title=title).exists():
                continue
            city, commune = rnd.choice(CITIES)
            listing = Listing.objects.create(
                seller=sellers[i % len(sellers)], category=subs[sub], title=title, brand=brand, price=price,
                description=f"{title}. Article en {('très bon', 'bon', 'parfait')[i % 3]} état, "
                            "photos réelles. Remise possible à Abidjan ou envoi par livreur.",
                condition=rnd.choice(Listing.Condition.values), quantity=rnd.choice([1, 1, 1, 2, 3]),
                city=city, commune=commune,
            )
            ListingImage.objects.create(listing=listing, image=placeholder_image(title, COLORS[i % len(COLORS)]))
        self.stdout.write(self.style.SUCCESS(
            "Démo prête : vendeurs awa / kouadio / fatou / yao (mot de passe demo12345!), "
            "administrateur admin / admin12345!"))
