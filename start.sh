#!/usr/bin/env bash
# Démarrage sur Render : le disque persistant n'est accessible qu'à l'exécution,
# donc les dossiers et les migrations sont faits ici, avant gunicorn.
set -o errexit
mkdir -p "$(dirname "${SQLITE_PATH:-var/db.sqlite3}")" "${MEDIA_ROOT:-media}" "${BACKUP_DIR:-var/backups}" "${LOG_DIR:-var}"
[ -n "$CACHE_DIR" ] && mkdir -p "$CACHE_DIR"
python manage.py migrate --noinput
exec gunicorn config.wsgi --bind "0.0.0.0:${PORT:-8000}" --workers "${WEB_CONCURRENCY:-2}" --threads 4 --timeout 60
