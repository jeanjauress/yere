from django.urls import path

from . import views

app_name = "listings"

urlpatterns = [
    path("", views.home, name="home"),
    path("catalogue/", views.search, name="search"),
    path("categorie/<slug:slug>/", views.search, name="category"),
    path("article/<int:pk>/", views.detail, name="detail_short"),
    path("article/<int:pk>/<slug:slug>/", views.detail, name="detail"),
    path("vendre/", views.create, name="create"),
    path("mes-annonces/", views.mine, name="mine"),
    path("mes-annonces/<int:pk>/modifier/", views.edit, name="edit"),
    path("mes-annonces/<int:pk>/<str:action>/", views.change_status, name="change_status"),
]
