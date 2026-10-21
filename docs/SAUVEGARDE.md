# Sauvegarde et restauration

## Sauvegarde

```bash
python manage.py backup_db            # garde les 14 dernières sauvegardes
python manage.py backup_db --keep 30
```

La commande utilise l'API de sauvegarde de SQLite : la copie est cohérente même si le site est en service.
Elle vérifie ensuite l'intégrité (`PRAGMA integrity_check`) et supprime la copie si elle est corrompue.
Les fichiers sont écrits dans `var/backups/` (ou `BACKUP_DIR`).

Les **photos** (`media/`) ne sont pas dans la base : les sauvegarder aussi, par exemple avec `rsync`.

### Automatiser (cron, toutes les 6 heures)

```cron
0 */6 * * * cd /srv/yere && set -a && . ./.env && .venv/bin/python manage.py backup_db >> var/backup.log 2>&1
30 2 * * * rsync -a /srv/yere/media/ /srv/backups/yere-media/
```

Copier régulièrement `BACKUP_DIR` hors du serveur (autre machine, stockage objet).

## Restauration

1. Arrêter le site : `sudo systemctl stop yere`.
2. Restaurer :
   ```bash
   python manage.py restore_db var/backups/db-20261021-180000.sqlite3
   ```
   La commande vérifie l'intégrité de la sauvegarde puis demande confirmation (`--yes` pour l'éviter).
3. Restaurer `media/` si nécessaire, puis redémarrer : `sudo systemctl start yere`.

## Tester la procédure

Le test `tests.test_moderation.BackupRestoreTests` vérifie l'aller-retour sauvegarde → modification →
restauration. Il est aussi recommandé de restaurer une sauvegarde réelle sur une machine de test une fois par mois.
