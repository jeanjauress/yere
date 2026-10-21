from django.urls import path

from . import views

app_name = "moderation"

urlpatterns = [
    path("signaler/annonce/<int:pk>/", views.report_listing, name="report_listing"),
    path("signaler/utilisateur/<str:username>/", views.report_user, name="report_user"),
    path("", views.dashboard, name="dashboard"),
    path("signalements/", views.reports, name="reports"),
    path("signalements/<int:pk>/", views.report_detail, name="report_detail"),
    path("annonces/", views.listings, name="listings"),
    path("annonces/<int:pk>/<str:action>/", views.listing_action, name="listing_action"),
    path("utilisateurs/", views.users, name="users"),
    path("utilisateurs/<int:pk>/<str:action>/", views.user_action, name="user_action"),
    path("commandes/", views.orders, name="orders"),
    path("avis/", views.reviews, name="reviews"),
    path("avis/<int:pk>/basculer/", views.review_toggle, name="review_toggle"),
    path("journal/", views.audit, name="audit"),
]
