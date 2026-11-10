from django.urls import path

from . import views

urlpatterns = [
    path("", views.MuroView.as_view(), name="muro"),
    path("destinos/", views.DestinosView.as_view(), name="muro-destinos"),
    path("<int:pk>/", views.PublicacionView.as_view(), name="muro-publicacion"),
    path("<int:pk>/reportar/", views.ReportarView.as_view(), name="muro-reportar"),
    path("<int:pk>/atender-reportes/", views.AtenderReportesView.as_view(), name="muro-atender"),
    path("<int:pk>/reaccion/", views.ReaccionView.as_view(), name="muro-reaccion"),
    path("<int:pk>/comentarios/", views.ComentariosView.as_view(), name="muro-comentarios"),
    path("<int:pk>/fotos/", views.FotosView.as_view(), name="muro-fotos"),
    path("fotos/<int:pk>/", views.FotoView.as_view(), name="muro-foto"),
    path("comentarios/<int:pk>/", views.ComentarioView.as_view(), name="muro-comentario"),
]
