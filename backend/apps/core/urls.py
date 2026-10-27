from django.urls import path

from .views import AuditListView, AuditResumenView, ConfigItemView, ConfigView, HealthView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("auditoria/", AuditListView.as_view(), name="auditoria"),
    path("auditoria/resumen/", AuditResumenView.as_view(), name="auditoria-resumen"),
    path("config/", ConfigView.as_view(), name="config"),
    path("config/<str:clave>/", ConfigItemView.as_view(), name="config-item"),
]
