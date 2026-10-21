import sqlite3
from datetime import datetime

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Sauvegarde à chaud de la base SQLite (API de backup SQLite, cohérente même en cours d'utilisation)."

    def add_arguments(self, parser):
        parser.add_argument("--keep", type=int, default=14, help="Nombre de sauvegardes à conserver.")

    def handle(self, *args, **opts):
        settings.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        target = settings.BACKUP_DIR / f"db-{datetime.now():%Y%m%d-%H%M%S}.sqlite3"
        src = sqlite3.connect(settings.SQLITE_PATH)
        dst = sqlite3.connect(target)
        with dst:
            src.backup(dst)
        check = dst.execute("PRAGMA integrity_check").fetchone()[0]
        src.close()
        dst.close()
        if check != "ok":
            target.unlink()
            raise SystemExit(f"Sauvegarde corrompue : {check}")
        backups = sorted(settings.BACKUP_DIR.glob("db-*.sqlite3"))
        for old in backups[:-opts["keep"]] if opts["keep"] > 0 else []:
            old.unlink()
        self.stdout.write(self.style.SUCCESS(f"Sauvegarde créée : {target}"))
