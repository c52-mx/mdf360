from django.urls import path

from . import views

urlpatterns = [
    path("", views.CatalogoFormulariosView.as_view(), name="formularios-catalogo"),
    path("<slug:entidad>/", views.FormularioView.as_view(), name="formulario"),
    path("<slug:entidad>/reporte/", views.ReporteView.as_view(), name="formulario-reporte"),
]
