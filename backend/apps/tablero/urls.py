from django.urls import path

from . import views

urlpatterns = [
    path("", views.TableroView.as_view(), name="tablero"),
    path("no-leidos/", views.NoLeidosView.as_view(), name="tablero-no-leidos"),
    path("mis-tableros/", views.MisTablerosView.as_view(), name="tablero-mis-tableros"),
    path("visto/", views.VistoView.as_view(), name="tablero-visto"),
    path("<int:pk>/", views.MensajeView.as_view(), name="tablero-mensaje"),
]
