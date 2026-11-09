from django.urls import path

from . import views

urlpatterns = [
    path("", views.MuroView.as_view(), name="muro"),
    path("destinos/", views.DestinosView.as_view(), name="muro-destinos"),
]
