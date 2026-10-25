from django.urls import path

from . import views, views_ofrendas

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
    path(
        "reuniones/<int:rid>/ofrendas/",
        views_ofrendas.OfrendasReunionView.as_view(),
        name="reunion-ofrendas",
    ),
    path(
        "ofrendas/pendientes/",
        views_ofrendas.OfrendasPendientesView.as_view(),
        name="ofrendas-pendientes",
    ),
    path("ofrendas/<int:oid>/", views_ofrendas.OfrendaView.as_view(), name="ofrenda"),
    path("ofrendas/<int:oid>/aval/", views_ofrendas.AvalView.as_view(), name="ofrenda-aval"),
    path("estudios/", views.EstudiosView.as_view(), name="estudios"),
    path(
        "estudios/<int:pk>/archivo/<str:tipo>/",
        views.EstudioArchivoView.as_view(),
        name="estudio-archivo",
    ),
]
