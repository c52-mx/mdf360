from django.urls import path

from . import views

urlpatterns = [
    path("", views.PeticionesView.as_view(), name="peticiones"),
    path("resumen/", views.ResumenView.as_view(), name="peticiones-resumen"),
    path("origenes/", views.OrigenesView.as_view(), name="peticiones-origenes"),
    path("formulario/", views.FormularioView.as_view(), name="peticiones-formulario"),
    path("<int:pk>/", views.PeticionView.as_view(), name="peticion"),
]
