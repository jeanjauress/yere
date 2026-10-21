from django.conf import settings
from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError


def validate_image_file(f):
    """Contrôle la taille et le contenu réel d'une image envoyée (pas seulement l'extension)."""
    if f.size > settings.UPLOAD_MAX_BYTES:
        raise ValidationError(
            "L'image dépasse la taille maximale de %(max)s Mo.",
            params={"max": settings.UPLOAD_MAX_BYTES // (1024 * 1024)},
        )
    pos = f.tell() if hasattr(f, "tell") else 0
    try:
        img = Image.open(f)
        fmt = img.format
        img.verify()
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise ValidationError("Le fichier envoyé n'est pas une image valide.")
    finally:
        f.seek(pos)
    if fmt not in settings.UPLOAD_ALLOWED_FORMATS:
        raise ValidationError("Formats acceptés : JPEG, PNG, WEBP.")
