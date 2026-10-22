#!/usr/bin/env bash
# Construction sur Render : dépendances et fichiers statiques.
set -o errexit
pip install -r requirements.txt
python manage.py collectstatic --noinput
