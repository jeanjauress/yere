from django.urls import path

from . import views

app_name = "reviews"

urlpatterns = [
    path("", views.mine, name="mine"),
    path("commande/<str:number>/", views.create, name="create"),
]
