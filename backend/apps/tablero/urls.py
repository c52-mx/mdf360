from django.urls import path

from . import views

urlpatterns = [
    path("", views.TableroView.as_view(), name="tablero"),
    path("no-leidos/", views.NoLeidosView.as_view(), name="tablero-no-leidos"),
    path("mis-tableros/", views.MisTablerosView.as_view(), name="tablero-mis-tableros"),
    path("destinos/", views.DestinosView.as_view(), name="tablero-destinos"),
    path("masivo/", views.MasivoView.as_view(), name="tablero-masivo"),
    path("por-autorizar/", views.PorAutorizarView.as_view(), name="tablero-por-autorizar"),
    path("<int:pk>/autorizar/", views.AutorizarAvisoView.as_view(), name="tablero-autorizar"),
    path("<int:pk>/rechazar/", views.RechazarAvisoView.as_view(), name="tablero-rechazar"),
    path("visto/", views.VistoView.as_view(), name="tablero-visto"),
    path("<int:pk>/", views.MensajeView.as_view(), name="tablero-mensaje"),
    path("<int:pk>/restaurar/", views.MensajeRestaurarView.as_view(), name="tablero-restaurar"),
]
