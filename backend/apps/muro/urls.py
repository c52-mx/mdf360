from django.urls import path

from . import views

urlpatterns = [
    path("", views.MuroView.as_view(), name="muro"),
    path("destinos/", views.DestinosView.as_view(), name="muro-destinos"),
    path("<int:pk>/reaccion/", views.ReaccionView.as_view(), name="muro-reaccion"),
    path("<int:pk>/comentarios/", views.ComentariosView.as_view(), name="muro-comentarios"),
    path("comentarios/<int:pk>/", views.ComentarioView.as_view(), name="muro-comentario"),
]
