from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("panier/", views.cart, name="cart"),
    path("panier/ajouter/<int:pk>/", views.cart_add, name="cart_add"),
    path("panier/<int:pk>/modifier/", views.cart_update, name="cart_update"),
    path("panier/<int:pk>/retirer/", views.cart_remove, name="cart_remove"),
    path("commande/validation/", views.checkout_view, name="checkout"),
    path("commandes/achats/", views.purchases, name="purchases"),
    path("commandes/ventes/", views.sales, name="sales"),
    path("commandes/<str:number>/", views.detail, name="detail"),
    path("commandes/<str:number>/statut/", views.seller_update, name="seller_update"),
    path("commandes/<str:number>/<str:action>/", views.buyer_action, name="buyer_action"),
]
