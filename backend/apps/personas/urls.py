from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views, views_perfil

router = DefaultRouter()
router.register("", views.PersonaViewSet, basename="persona")

# Las rutas fijas van antes del router para que no se confundan con un identificador.
urlpatterns = [
    path("mi-perfil/", views_perfil.MiPerfilView.as_view(), name="mi-perfil"),
    path("mi-perfil/foto/", views_perfil.MiFotoView.as_view(), name="mi-perfil-foto"),
    path("mi-perfil/vehiculos/", views_perfil.MisVehiculosView.as_view(), name="mis-vehiculos"),
    path(
        "mi-perfil/vehiculos/<int:pk>/", views_perfil.MiVehiculoView.as_view(), name="mi-vehiculo"
    ),
    path("aviso-privacidad/", views.AvisoPrivacidadView.as_view(), name="aviso-privacidad"),
    path("catalogo/procesos/", views.CatalogoProcesosView.as_view(), name="catalogo-procesos"),
    path("", include(router.urls)),
]
