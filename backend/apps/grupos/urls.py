from django.urls import path

from . import views

urlpatterns = [
    path("", views.GruposView.as_view(), name="grupos"),
    path("<int:pk>/", views.GrupoView.as_view(), name="grupo"),
    path("<int:pk>/integrantes/", views.IntegrantesView.as_view(), name="grupo-integrantes"),
    path(
        "<int:pk>/integrantes/<int:miembro_id>/",
        views.IntegranteView.as_view(),
        name="grupo-integrante",
    ),
    path("<int:pk>/reuniones/", views.ReunionesView.as_view(), name="grupo-reuniones"),
    path("reuniones/<int:rid>/", views.ReunionView.as_view(), name="reunion"),
    path("estudios/", views.EstudiosView.as_view(), name="estudios"),
    path(
        "estudios/<int:pk>/archivo/<str:tipo>/",
        views.EstudioArchivoView.as_view(),
        name="estudio-archivo",
    ),
]
