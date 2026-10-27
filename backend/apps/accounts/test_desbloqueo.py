from datetime import timedelta

from django.utils import timezone

from apps.core.models import AuditEvent
from apps.tablero.test_tablero import PIN, api_de, m  # noqa: F401


def bloquear(user):
    user.locked_until = timezone.now() + timedelta(minutes=15)
    user.failed_attempts = 0
    user.save(update_fields=["locked_until", "failed_attempts"])


def test_el_lider_desbloquea_a_alguien_de_su_grupo(m):  # noqa: F811
    bloquear(m["asistente"])
    r = api_de(m["lider"]).post(f"/api/auth/users/{m['asistente'].pk}/unlock/")
    assert r.status_code == 204
    m["asistente"].refresh_from_db()
    assert not m["asistente"].is_locked()
    assert AuditEvent.objects.filter(
        action="auth.unlocked", target_id=str(m["asistente"].pk)
    ).exists()


def test_el_desbloqueo_no_cambia_el_pin(m):  # noqa: F811
    bloquear(m["asistente"])
    api_de(m["lider"]).post(f"/api/auth/users/{m['asistente'].pk}/unlock/")
    m["asistente"].refresh_from_db()
    assert m["asistente"].check_password(PIN)


def test_el_lider_no_alcanza_a_gente_de_otro_grupo(m):  # noqa: F811
    bloquear(m["otro"])
    r = api_de(m["lider"]).post(f"/api/auth/users/{m['otro'].pk}/unlock/")
    assert r.status_code == 404
    m["otro"].refresh_from_db()
    assert m["otro"].is_locked()


def test_el_pastor_desbloquea_a_cualquiera(m):  # noqa: F811
    bloquear(m["otro"])
    assert api_de(m["pastor"]).post(f"/api/auth/users/{m['otro'].pk}/unlock/").status_code == 204


def test_sin_permiso_no_desbloquea(m):  # noqa: F811
    bloquear(m["otro"])
    r = api_de(m["asistente"]).post(f"/api/auth/users/{m['otro'].pk}/unlock/")
    assert r.status_code == 403


def test_reiniciar_acceso_tambien_respeta_el_alcance(m):  # noqa: F811
    assert api_de(m["lider"]).post(f"/api/auth/users/{m['otro'].pk}/reset/").status_code == 404
    assert api_de(m["lider"]).post(f"/api/auth/users/{m['asistente'].pk}/reset/").status_code == 200


def test_listado_de_accesos_por_alcance_y_busqueda(m):  # noqa: F811
    bloquear(m["asistente"])
    filas = api_de(m["lider"]).get("/api/auth/accesos/").json()
    nombres = {f["nombre"] for f in filas}
    assert "Ana Asistente" in nombres
    assert "Olga de otro grupo" not in nombres
    assert "Laura Líder" not in nombres  # no se lista a sí misma
    ana = next(f for f in filas if f["nombre"] == "Ana Asistente")
    assert ana["bloqueado"] is True
    filtradas = api_de(m["lider"]).get("/api/auth/accesos/?q=ana").json()
    assert [f["nombre"] for f in filtradas] == ["Ana Asistente"]
    todos = {f["nombre"] for f in api_de(m["pastor"]).get("/api/auth/accesos/").json()}
    assert "Olga de otro grupo" in todos


def test_el_listado_exige_permiso(m):  # noqa: F811
    assert api_de(m["asistente"]).get("/api/auth/accesos/").status_code == 403
