def test_health_responde_ok(client):
    response = client.get("/api/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ---------- bitácora: refuerzo en la base de datos y consulta ----------
import pytest  # noqa: E402
from django.db import connection, transaction  # noqa: E402
from rest_framework.test import APIClient  # noqa: E402

from apps.accounts.models import AsignacionRol, Rol, User  # noqa: E402

from .models import AuditEvent  # noqa: E402


@pytest.mark.django_db
def test_la_base_de_datos_rechaza_update_delete_y_truncate():
    evento = AuditEvent.objects.create(action="prueba")
    for sql in (
        "UPDATE core_auditevent SET action='x'",
        "DELETE FROM core_auditevent",
        "TRUNCATE core_auditevent",
    ):
        with pytest.raises(Exception, match="solo-añadir|pending trigger"), transaction.atomic():
            with connection.cursor() as cur:
                cur.execute(sql)
    assert AuditEvent.objects.filter(pk=evento.pk, action="prueba").exists()


def _usuario(whatsapp, rol):
    user = User.objects.create_user(whatsapp, pin="482915", nombre=rol)
    AsignacionRol.objects.create(usuario=user, rol=Rol.objects.get(clave=rol))
    return user


@pytest.mark.django_db
def test_consulta_de_bitacora_por_permiso_y_filtros():
    sin = APIClient()
    sin.force_authenticate(_usuario("55 1000 0001", "lider"))
    assert sin.get("/api/auditoria/").status_code == 403
    admin = APIClient()
    admin.force_authenticate(_usuario("55 1000 0002", "admin_tecnico"))
    AuditEvent.objects.create(action="persona.created", actor_repr="Ana")
    AuditEvent.objects.create(action="auth.login", actor_repr="Beto")
    todo = admin.get("/api/auditoria/").json()
    assert todo["count"] == 2
    assert admin.get("/api/auditoria/?action=auth").json()["count"] == 1
    assert admin.get("/api/auditoria/?q=Ana").json()["results"][0]["actor"] == "Ana"
    assert AuditEvent.objects.filter(action="bitacora.viewed").exists()
