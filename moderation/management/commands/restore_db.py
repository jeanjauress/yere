import sqlite3

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Restaure la base SQLite depuis une sauvegarde. Arrêter le serveur avant de lancer cette commande."

    def add_arguments(self, parser):
        parser.add_argument("backup", help="Chemin du fichier de sauvegarde (.sqlite3).")
        parser.add_argument("--yes", action="store_true", help="Ne pas demander de confirmation.")

    def handle(self, *args, **opts):
        from pathlib import Path

        source = Path(opts["backup"])
        if not source.exists():
            raise CommandError(f"Fichier introuvable : {source}")
        src = sqlite3.connect(source)
        if src.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise CommandError("La sauvegarde est corrompue, restauration annulée.")
        if not opts["yes"]:
            answer = input(f"Remplacer {settings.SQLITE_PATH} par {source} ? [oui/non] ")
            if answer.strip().lower() not in ("oui", "o", "yes", "y"):
                raise CommandError("Restauration annulée.")
        dst = sqlite3.connect(settings.SQLITE_PATH)
        with dst:
            src.backup(dst)
        src.close()
        dst.close()
        self.stdout.write(self.style.SUCCESS("Base restaurée."))
