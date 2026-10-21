# Guide d'utilisation

## Acheteurs

1. **Trouver un article** : barre de recherche, catégories, puis filtres (prix, état, marque, ville) et tri.
2. **Favoris** : cliquer sur le cœur. Retrouver la liste dans le menu → Favoris.
3. **Poser une question** au vendeur depuis la fiche article (« Poser une question »).
4. **Acheter** : « Acheter » ou « Ajouter au panier », puis renseigner la livraison (nom, téléphone, adresse,
   commune, ville, mode de livraison) et confirmer. Le paiement se fait à la livraison.
   Si le panier contient des articles de plusieurs vendeurs, une commande est créée par vendeur.
5. **Suivre la commande** : menu → Mes achats. Vous pouvez annuler tant que le vendeur n'a pas confirmé.
   À la réception, cliquer sur « J'ai reçu ma commande ».
6. **Laisser un avis** (1 à 5 étoiles) une fois la commande livrée. Un seul avis par commande.

## Vendeurs

1. **Déposer un article** : bouton « Vendre ». Titre, catégorie, description, état, prix en FCFA, quantité,
   ville, et au moins une photo (8 au maximum, JPEG/PNG/WEBP, 5 Mo chacune). Cocher « brouillon » pour publier plus tard.
2. **Gérer ses annonces** : menu → Mes annonces : modifier, désactiver, publier, marquer comme vendue, supprimer.
   Une annonce dont le stock tombe à 0 passe automatiquement en « vendue ».
3. **Traiter une vente** : une notification arrive à chaque commande. Dans Mes ventes → la commande, faire
   évoluer le statut : Confirmée → En préparation → Expédiée (ajouter une note de suivi : livreur, référence…)
   → Livrée. Une commande annulée remet l'article en stock.

## Sécurité et signalements

- Bloquer un utilisateur depuis une conversation ou son profil : il ne peut plus vous écrire.
- « Signaler » sur une annonce ou un profil envoie le cas à la modération.
- Ne communiquez jamais de code Mobile Money ou de code de carte bancaire.

## Modérateurs / administrateurs

Accès : menu → Administration (`/moderation/`). Un compte administrateur se crée avec
`python manage.py createsuperuser`, ou en donnant le rôle « Administrateur » à un utilisateur dans l'admin Django.

- **Statistiques** : utilisateurs, annonces, commandes et volume sur 30 jours, signalements ouverts.
- **Signalements** : examiner, puis classer sans suite, suspendre l'annonce, suspendre le compte ou marquer
  comme traité. Le signaleur et la personne concernée sont notifiés.
- **Annonces / Utilisateurs** : rechercher, suspendre, rétablir, supprimer. Un compte suspendu est
  déconnecté immédiatement et ses annonces disparaissent du catalogue.
- **Commandes** et **Avis** : suivi ; un avis abusif peut être masqué.
- **Journal** : toutes les actions sensibles (qui, quoi, quand, IP).
- **Admin Django** (`/gestion-admin/` par défaut) : catégories et sous-catégories, gestion détaillée.
