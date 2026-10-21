# Schéma de la base SQLite

Les tables sont créées par les migrations Django (`python manage.py migrate`), à partir des fichiers
`*/migrations/*.py`. Les montants sont des **entiers en XOF**. Les dates sont stockées en UTC.

## accounts_user
| Champ | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| username | TEXT unique | |
| email | TEXT unique | |
| password | TEXT | empreinte PBKDF2, jamais en clair |
| first_name, last_name | TEXT | |
| phone | TEXT | facultatif |
| profile_image | TEXT | chemin dans `media/avatars/` |
| bio, city | TEXT | |
| role | TEXT | `user` ou `admin` (admin ⇒ is_staff) |
| email_verified, is_active, is_suspended, is_staff, is_superuser | INTEGER (bool) | |
| date_joined, last_login | TEXT (datetime) | |

## listings_category
id · name · slug (unique) · parent_id → category (PROTECT) · icon · position · is_active

## listings_listing
| Champ | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| seller_id | → accounts_user (CASCADE) | |
| category_id | → listings_category (PROTECT) | |
| title, slug, description, brand, size | TEXT | |
| condition | TEXT | `new`, `very_good`, `good`, `fair` |
| price | INTEGER | CHECK ≥ 0 |
| quantity | INTEGER | CHECK ≥ 0 |
| city, commune | TEXT | |
| status | TEXT | `draft`, `pending`, `published`, `inactive`, `sold`, `suspended`, `deleted` |
| views_count | INTEGER | |
| created_at, updated_at | TEXT (datetime) | |

Index : (status, created_at), (status, price), (category, status), city, brand.

## listings_listingimage
id · listing_id → listing (CASCADE) · image (chemin dans `media/listings/`) · position

## favorites_favorite
id · user_id · listing_id · created_at — **UNIQUE (user_id, listing_id)**

## orders_cartitem
id · user_id · listing_id · quantity · added_at — UNIQUE (user_id, listing_id)

## orders_order
| Champ | Notes |
|---|---|
| order_number | unique, ex. `CMD-20261021-4A1E76` |
| buyer_id, seller_id | → accounts_user (PROTECT) — une commande par vendeur |
| items_amount, delivery_fee, total_amount | INTEGER XOF, calculés côté serveur |
| status | `pending`, `confirmed`, `preparing`, `shipped`, `delivered`, `cancelled`, `refunded` |
| payment_method, payment_status | `cod` ; `unpaid`, `pending`, `paid`, `failed`, `refunded` |
| delivery_mode, recipient_name, recipient_phone, delivery_address, commune, city, tracking_note, buyer_note | livraison |
| created_at, updated_at, delivered_at | |

Index : (buyer, created_at), (seller, created_at), status.

## orders_orderitem
id · order_id (CASCADE) · listing_id (SET NULL) · title · unit_price · quantity — copie figée au moment de l'achat.

## orders_payment
id · order_id · provider · amount · status (`pending`, `succeeded`, `failed`, `refunded`) · reference (externe) ·
created_at · confirmed_at. Aucune donnée de carte ni code Mobile Money.

## messaging_conversation
id · listing_id (SET NULL) · buyer_id · seller_id · created_at · updated_at — UNIQUE (listing, buyer, seller)

## messaging_message
id · conversation_id · sender_id · body · created_at · read_at (NULL = non lu)

## messaging_block
id · blocker_id · blocked_id · created_at — UNIQUE (blocker, blocked)

## reviews_review
id · order_id (**UNIQUE** : un avis par transaction) · author_id · seller_id · rating (CHECK 1–5) · comment ·
is_hidden · created_at

## notifications_notification
id · user_id · kind · message · url · is_read · created_at — index (user, is_read)

## moderation_report
id · reporter_id · listing_id · reported_user_id · reason · details · status (`open`, `resolved`, `dismissed`) ·
decision · handled_by_id · handled_at · created_at

## moderation_auditlog
id · actor_id · action (ex. `listing.suspend`) · target_type · target_id · target_repr · details · ip_address ·
created_at — non modifiable depuis l'administration.

Pour afficher le SQL exact d'une table : `python manage.py sqlmigrate orders 0001`.
