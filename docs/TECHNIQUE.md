# Documentation technique

## Architecture

Application Django monolithique, une app par domaine du cahier des charges (voir README). Les règles métier
sensibles sont regroupées dans des modules de services testés :

- `orders/services.py` — `checkout()` (validation transactionnelle du panier), `change_status()` (transitions,
  remise en stock, paiement à la livraison), `cart_summary()` (montants recalculés côté serveur).
- `orders/payments.py` — interface des moyens de paiement.
- `moderation/audit.py` — `log_action()` écrit dans le journal d'audit.
- `notifications/services.py` — `notify()` crée une notification (point d'extension e-mail / SMS).

### SQLite

Réglages dans `config/settings.py` :

- fichier dans `var/` (hors de `static/` et `media/`), chemin modifiable avec `SQLITE_PATH` ;
- `PRAGMA journal_mode=WAL` (lectures pendant les écritures), `foreign_keys=ON`, `synchronous=NORMAL` ;
- `transaction_mode=IMMEDIATE` et `timeout=20` : chaque transaction prend le verrou d'écriture au début, ce qui
  évite les erreurs « database is locked » et sérialise les validations de commande ;
- index sur les colonnes recherchées (statut + date, statut + prix, catégorie, ville, marque, commandes par
  acheteur / vendeur, notifications non lues…) et contraintes `CHECK` (prix ≥ 0, quantité ≥ 0, note 1–5),
  contraintes d'unicité (favori, article du panier, conversation, blocage, un avis par commande).

**Quand passer à PostgreSQL :** plusieurs serveurs d'application, écritures très concurrentes (dizaines de
commandes par seconde), ou besoin de haute disponibilité. Le code n'utilise que l'ORM : la migration consiste à
changer `DATABASES`, lancer `migrate`, puis transférer les données (`dumpdata` / `loaddata`).

### Anti-survente

`_reserve_stock()` exécute `UPDATE listing SET quantity = quantity - n WHERE id = ? AND status = 'published' AND
quantity >= n`. Si aucune ligne n'est modifiée, une `CheckoutError` est levée et toute la transaction (commandes
déjà créées pour d'autres vendeurs comprises) est annulée. Le test `ConcurrentCheckoutTests` lance 6 achats
simultanés du dernier exemplaire et vérifie qu'un seul aboutit.

## Sécurité

| Exigence | Mise en œuvre |
|---|---|
| Mots de passe | Hachage PBKDF2 (Django), validateurs de complexité (8 caractères min.) |
| Injections SQL | ORM uniquement, aucune requête SQL concaténée |
| XSS | Échappement automatique des gabarits ; aucun contenu utilisateur marqué `safe` |
| CSRF | Middleware CSRF, toutes les actions qui modifient des données sont en POST |
| Fichiers envoyés | Taille max 5 Mo, contenu vérifié avec Pillow (JPEG/PNG/WEBP), noms de fichiers aléatoires |
| Tentatives de connexion | 5 échecs par IP + identifiant → blocage 15 min (`LOGIN_MAX_ATTEMPTS`, `LOGIN_LOCKOUT_SECONDS`) |
| Contrôle d'accès | Annonces modifiables par leur propriétaire seul ; conversations et commandes visibles par leurs participants ; pages de modération réservées au personnel ; comptes suspendus déconnectés immédiatement |
| Redirections | Paramètres `next` validés (`url_has_allowed_host_and_scheme`) |
| Admin | URL configurable (`DJANGO_ADMIN_URL`), rôle `admin` distinct, journal d'audit non modifiable |
| Production | `DEBUG=false` active HTTPS forcé, cookies sécurisés, HSTS, `X-Frame-Options: DENY`, nosniff |

Le cache de limitation de connexion est en mémoire locale : avec plusieurs processus gunicorn, chaque processus
compte séparément. Pour un comptage global, configurer un cache partagé (`FileBasedCache` ou Redis) dans `CACHES`.

## Déploiement (exemple Ubuntu + gunicorn + nginx)

```bash
sudo apt install python3-venv nginx
git clone <dépôt> /srv/yere && cd /srv/yere
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env   # puis remplir les valeurs
set -a; . ./.env; set +a
.venv/bin/python manage.py migrate
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/python manage.py seed_demo            # catégories uniquement
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py check --deploy
```

Service systemd (`/etc/systemd/system/yere.service`) :

```ini
[Service]
WorkingDirectory=/srv/yere
EnvironmentFile=/srv/yere/.env
ExecStart=/srv/yere/.venv/bin/gunicorn config.wsgi:application --bind 127.0.0.1:8001 --workers 3
User=www-data
Restart=always
[Install]
WantedBy=multi-user.target
```

nginx sert `/static/` depuis `staticfiles/` et `/media/` depuis `media/`, transmet le reste à gunicorn, et
n'expose jamais `var/`. Certificat HTTPS : `certbot --nginx`. Limiter `client_max_body_size` à 45 Mo
(8 photos × 5 Mo).

Surveillance des erreurs : les erreurs serveur sont écrites dans `var/errors.log`. On peut ajouter Sentry
(`sentry-sdk`) en une ligne dans les réglages.

## Ajouter un moyen de paiement

1. Créer une classe dans `orders/payments.py` qui hérite de `PaymentProvider` :
   - `start(order)` crée un `Payment` en attente, appelle l'API du prestataire et retourne l'URL de paiement ;
   - le webhook du prestataire (vue à créer, signature vérifiée) appelle `provider.confirm(payment, reference)`.
2. L'ajouter à `PROVIDERS` et son code à `settings.PAYMENT_METHODS`.
3. Dans `checkout_view`, rediriger vers l'URL retournée par `start()` si elle existe.

La commande ne passe « payée » qu'après confirmation par le prestataire. Ne jamais stocker de numéro de carte
ni de code Mobile Money : seule la référence de transaction est conservée.

## Évolutions prévues

API REST (Django REST Framework) pour l'application mobile, paiements Mobile Money automatisés, transporteurs,
e-mails / SMS de notification (brancher dans `notify()`), recommandations, codes promo, boutiques pro, migration
PostgreSQL.
