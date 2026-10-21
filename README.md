# Yere — marketplace d'articles d'occasion (Côte d'Ivoire)

Première version (V1) de la plateforme décrite dans le cahier des charges du 21 octobre 2026 :
vente et achat d'articles neufs ou d'occasion entre particuliers et professionnels, prix en francs CFA (XOF).

**Pile technique :** Python 3.11+ · Django 5.2 · SQLite (mode WAL) · Bootstrap 5 (servi localement) · Pillow.

> « Yere » est un nom provisoire : il se change avec la variable `SITE_NAME`.

## Démarrage rapide

```bash
python -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo --demo  # catégories + comptes et annonces de démonstration
python manage.py runserver
```

Ouvrir http://127.0.0.1:8000.

| Compte de démo | Mot de passe | Rôle |
|---|---|---|
| `awa`, `kouadio`, `fatou`, `yao` | `demo12345!` | vendeurs / acheteurs |
| `admin` | `admin12345!` | administrateur (modération : `/moderation/`, admin Django : `/gestion-admin/`) |

Sans `--demo`, `seed_demo` ne crée que les catégories. Pour créer un vrai administrateur :
`python manage.py createsuperuser`.

Les e-mails (confirmation d'adresse, mot de passe oublié) s'affichent dans la console en développement.

## Tests

```bash
python manage.py test tests
```

49 tests couvrent : inscription / connexion / vérification e-mail / limitation des tentatives / réinitialisation,
annonces (création, contrôle des images, droits du propriétaire, statuts), recherche, filtres, tri et pagination,
favoris, panier, commandes et transitions de statut, **achats simultanés du dernier exemplaire (6 threads, une seule
vente)**, annulation avec remise en stock, messagerie et contrôle d'accès, blocage, échappement XSS, avis
(transaction admissible, un seul avis), modération, journal d'audit, sauvegarde et restauration SQLite.

## Fonctionnalités de la V1

| Espace | Contenu |
|---|---|
| Public | Accueil (nouveautés, populaires, recommandations), catalogue par catégorie / sous-catégorie, recherche par mot-clé, filtres prix / état / marque / ville, tri, pagination, fiche article, profil public vendeur avec avis, sitemap.xml, robots.txt |
| Compte | Inscription, connexion par nom d'utilisateur ou e-mail, vérification de l'e-mail, mot de passe oublié, changement de mot de passe, profil et photo, désactivation du compte, limitation des tentatives de connexion |
| Vendeur | Dépôt d'annonce (jusqu'à 8 photos JPEG/PNG/WEBP de 5 Mo max, contenu vérifié), brouillon, modification, désactivation, « vendue », suppression, suivi des ventes et mise à jour des statuts de commande |
| Acheteur | Favoris, panier (quantités limitées au stock), validation en une page, une commande par vendeur, historique et suivi, annulation tant que la commande n'est pas confirmée, confirmation de réception, avis 1 à 5 étoiles |
| Messagerie | Conversations liées à une annonce, lu / non lu, blocage, signalement d'un utilisateur |
| Notifications | Nouveau message, commande reçue, article vendu, changement de statut, nouvel avis, décisions de modération |
| Administration | `/moderation/` : statistiques, signalements et décisions, suspension / rétablissement d'annonces et de comptes, suivi des commandes, masquage d'avis, journal d'audit. Admin Django pour les catégories et la gestion fine |

### Commandes, stock et paiement

- Statuts : en attente de confirmation → confirmée → en préparation → expédiée → livrée ; annulée ; remboursée (admin).
  Les transitions autorisées sont définies dans `Order.TRANSITIONS`.
- La validation du panier se fait dans **une seule transaction** : décrément conditionnel du stock
  (`UPDATE … WHERE quantity >= n`) puis création des commandes. Si un article n'est plus disponible,
  rien n'est enregistré. SQLite est configuré en `transaction_mode=IMMEDIATE` pour sérialiser les écritures.
- Tous les montants (articles, livraison, total) sont recalculés côté serveur ; le prix est figé dans `OrderItem`.
- Paiement V1 : **paiement à la livraison** uniquement. La commande passe « payée » quand elle est livrée.
  `orders/payments.py` définit l'interface pour brancher un prestataire Mobile Money / carte
  (voir [docs/TECHNIQUE.md](docs/TECHNIQUE.md#ajouter-un-moyen-de-paiement)). Aucune donnée de carte ni code
  Mobile Money n'est stocké.
- Livraison : gérée manuellement par le vendeur (note de suivi). Modes et frais dans `settings.DELIVERY_MODES`
  (remise en main propre 0 F, Abidjan 1 500 F, hors Abidjan 3 000 F — à ajuster).

## Organisation du code

```
config/         réglages, URL racine, processeur de contexte
accounts/       utilisateur personnalisé, authentification, profil, limitation de connexion
listings/       catégories, annonces, photos, catalogue, recherche, commande seed_demo
favorites/      favoris
orders/         panier, commandes, paiements (interface), services transactionnels
messaging/      conversations, messages, blocages
reviews/        avis
notifications/  notifications sur le site
moderation/     signalements, journal d'audit, tableau de bord admin, sauvegarde / restauration
templates/      pages HTML (Bootstrap)
static/         CSS, JS, Bootstrap et icônes (servis localement)
media/          photos envoyées (hors base)
var/            base SQLite, sauvegardes, journal d'erreurs (jamais servi au navigateur)
tests/          tests automatisés
docs/           documentation technique, schéma de base, guide d'utilisation, sauvegarde
```

## Documentation

- [docs/TECHNIQUE.md](docs/TECHNIQUE.md) — architecture, sécurité, déploiement en production, évolutions.
- [docs/SCHEMA.md](docs/SCHEMA.md) — schéma de la base SQLite.
- [docs/SAUVEGARDE.md](docs/SAUVEGARDE.md) — procédure de sauvegarde et de restauration.
- [docs/GUIDE_UTILISATEUR.md](docs/GUIDE_UTILISATEUR.md) — guide pour les utilisateurs et les modérateurs.

## Reste à faire avant la mise en production

- Choisir le nom et l'identité visuelle, compléter les pages légales (modèles fournis, à valider par un juriste ;
  déclaration ARTCI pour les données personnelles).
- Configurer l'hébergement, HTTPS, l'envoi d'e-mails (SMTP) et la sauvegarde automatique (voir docs).
- Intégrer un prestataire Mobile Money (CinetPay, PayDunya…) si le paiement en ligne est retenu.
