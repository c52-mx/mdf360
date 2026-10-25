from django.urls import path

from .views import AuditListView, ConfigItemView, ConfigView, HealthView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("auditoria/", AuditListView.as_view(), name="auditoria"),
    path("config/", ConfigView.as_view(), name="config"),
    path("config/<str:clave>/", ConfigItemView.as_view(), name="config-item"),
]
