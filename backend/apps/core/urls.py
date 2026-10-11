from django.urls import path

from .views import AuditListView, HealthView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("auditoria/", AuditListView.as_view(), name="auditoria"),
]
