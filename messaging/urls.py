from django.urls import path

from . import views

app_name = "messaging"

urlpatterns = [
    path("", views.inbox, name="inbox"),
    path("nouveau/<int:listing_pk>/", views.start, name="start"),
    path("<int:pk>/", views.thread, name="thread"),
    path("bloquer/<str:username>/", views.toggle_block, name="toggle_block"),
]
