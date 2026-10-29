from django.urls import path

from . import views

urlpatterns = [
    path("", views.UnidadesView.as_view(), name="unidades"),
    path("<int:pk>/", views.UnidadView.as_view(), name="unidad"),
    path("<int:pk>/integrantes/", views.IntegrantesView.as_view(), name="unidad-integrantes"),
    path(
        "<int:pk>/integrantes/<int:miembro_id>/",
        views.IntegranteView.as_view(),
        name="unidad-integrante",
    ),
    path(
        "<int:pk>/integrantes/<int:miembro_id>/restaurar/",
        views.IntegranteRestaurarView.as_view(),
        name="unidad-integrante-restaurar",
    ),
]
