from django.urls import path

from . import views

urlpatterns = [
    path("config/", views.ConfigView.as_view(), name="notificaciones-config"),
    path("suscribir/", views.SuscribirView.as_view(), name="notificaciones-suscribir"),
    path("desuscribir/", views.DesuscribirView.as_view(), name="notificaciones-desuscribir"),
    path("probar/", views.ProbarView.as_view(), name="notificaciones-probar"),
]
