#!/usr/bin/env bash
# Démarrage sur Render : le disque persistant n'est accessible qu'à l'exécution,
# donc les dossiers et les migrations sont faits ici, avant gunicorn.
set -o errexit
mkdir -p "$(dirname "${SQLITE_PATH:-var/db.sqlite3}")" "${MEDIA_ROOT:-media}" "${BACKUP_DIR:-var/backups}" "${LOG_DIR:-var}"
[ -n "$CACHE_DIR" ] && mkdir -p "$CACHE_DIR"
python manage.py migrate --noinput
# Offre gratuite (sans disque) : la base repart de zéro à chaque démarrage,
# on peut donc la remplir d'exemples et recréer le compte administrateur.
if [ "$SEED_DEMO" = "true" ]; then
  python manage.py seed_demo --demo
fi
if [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  python manage.py shell -c "
import os
from django.contrib.auth import get_user_model
User = get_user_model()
name = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
u = User.objects.filter(username=name).first() or User(username=name, email=os.environ.get('DJANGO_SUPERUSER_EMAIL', ''))
u.is_staff = u.is_superuser = True
u.role = 'admin'
u.email_verified = True
u.set_password(os.environ['DJANGO_SUPERUSER_PASSWORD'])
u.save()
"
fi
exec gunicorn config.wsgi --bind "0.0.0.0:${PORT:-8000}" --workers "${WEB_CONCURRENCY:-2}" --threads 4 --timeout 60
