from datetime import timedelta

import pytest
from django.core import mail
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.models import AppendOnlyError, AuditEvent

from .models import ActivationToken, User

PIN = "482915"


@pytest.fixture(autouse=True)
def _limpiar_cache():
    cache.clear()


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def laura(db):
    return User.objects.create_user(
        "55 1111 2222", pin=PIN, nombre="Laura Pérez", email="Laura@Example.com"
    )


@pytest.fixture
def staff(db):
    return User.objects.create_user("55 9999 0000", pin=PIN, nombre="Admin", is_staff=True)


def login(api, identifier="5511112222", credential=PIN):
    return api.post(
        "/api/auth/login/", {"identifier": identifier, "credential": credential}, format="json"
    )


# ---------- entrar ----------
def test_entra_con_whatsapp_y_pin(api, laura):
    r = login(api)
    assert r.status_code == 200
    assert r.json()["nombre"] == "Laura Pérez"
    assert api.get("/api/auth/me/").json()["whatsapp"] == "+525511112222"


def test_entra_con_correo_sin_importar_mayusculas(api, laura):
    assert login(api, "LAURA@example.com").status_code == 200


def test_pin_incorrecto_y_cuenta_inexistente_dan_el_mismo_mensaje(api, laura):
    malo = login(api, credential="000001")
    inexistente = login(api, identifier="5500000000")
    assert malo.status_code == inexistente.status_code == 400
    assert malo.json() == inexistente.json()


def test_bloqueo_tras_cinco_intentos(api, laura, settings):
    for _ in range(settings.AUTH_LOCKOUT_ATTEMPTS):
        assert login(api, credential="000001").status_code == 400
    r = login(api)  # aun con el PIN correcto
    assert r.status_code == 429
    assert r.json()["code"] == "locked"
    assert AuditEvent.objects.filter(action="auth.locked").exists()


def test_el_bloqueo_expira(api, laura):
    laura.locked_until = timezone.now() - timedelta(minutes=1)
    laura.save()
    assert login(api).status_code == 200


def test_cuenta_sin_pin_no_puede_entrar(api, db):
    User.objects.create_user("55 3333 4444", nombre="Sin PIN")
    assert login(api, "5533334444", "").status_code == 400
    assert login(api, "5533334444", "482915").status_code == 400


def test_cerrar_sesion(api, laura):
    login(api)
    assert api.post("/api/auth/logout/").status_code == 204
    assert api.get("/api/auth/me/").status_code == 403


# ---------- invitación y activación ----------
def test_invitar_exige_personal_autorizado(api, laura):
    datos = {"whatsapp": "5544445555", "nombre": "Pedro Gómez"}
    assert api.post("/api/auth/invitations/", datos, format="json").status_code == 403
    api.force_authenticate(laura)
    assert api.post("/api/auth/invitations/", datos, format="json").status_code == 403


def invitar(api, staff, **extra):
    api.force_authenticate(staff)
    datos = {"whatsapp": "5544445555", "nombre": "Pedro Gómez", **extra}
    r = api.post("/api/auth/invitations/", datos, format="json")
    api.force_authenticate(None)
    return r


def test_flujo_completo_de_activacion(api, staff):
    r = invitar(api, staff)
    assert r.status_code == 201
    body = r.json()
    assert body["whatsapp_url"].startswith("https://wa.me/525544445555?text=")
    token = body["activation_url"].rsplit("/", 1)[1]

    check = api.post("/api/auth/activation/check/", {"token": token}, format="json")
    assert check.status_code == 200 and check.json()["nombre"] == "Pedro Gómez"

    debil = api.post(
        "/api/auth/activation/complete/", {"token": token, "credential": "123456"}, format="json"
    )
    assert debil.status_code == 400 and debil.json()["code"] == "weak_credential"

    ok = api.post(
        "/api/auth/activation/complete/", {"token": token, "credential": PIN}, format="json"
    )
    assert ok.status_code == 200
    assert api.get("/api/auth/me/").json()["nombre"] == "Pedro Gómez"

    reuso = api.post(
        "/api/auth/activation/complete/", {"token": token, "credential": PIN}, format="json"
    )
    assert reuso.status_code == 400 and reuso.json()["code"] == "invalid_token"
    assert login(APIClient(), "5544445555").status_code == 200


def test_enlace_caducado_no_sirve(api, staff):
    body = invitar(api, staff).json()
    token = body["activation_url"].rsplit("/", 1)[1]
    ActivationToken.objects.update(expires_at=timezone.now() - timedelta(minutes=1))
    r = api.post("/api/auth/activation/check/", {"token": token}, format="json")
    assert r.status_code == 400


def test_invitar_de_nuevo_invalida_el_enlace_anterior(api, staff):
    primero = invitar(api, staff).json()["activation_url"].rsplit("/", 1)[1]
    segundo = invitar(api, staff).json()["activation_url"].rsplit("/", 1)[1]
    assert primero != segundo
    r = api.post("/api/auth/activation/check/", {"token": primero}, format="json")
    assert r.status_code == 400
    r = api.post("/api/auth/activation/check/", {"token": segundo}, format="json")
    assert r.status_code == 200


def test_no_se_invita_a_quien_ya_tiene_cuenta(api, staff, laura):
    r = invitar(api, staff, whatsapp="55 1111 2222")
    assert r.status_code == 409 and r.json()["code"] == "exists"


def test_staff_reinicia_el_acceso(api, staff, laura):
    api.force_authenticate(staff)
    r = api.post(f"/api/auth/users/{laura.pk}/reset/")
    assert r.status_code == 200
    assert "reiniciar tu acceso" in r.json()["whatsapp_url"].replace("%20", " ")
    assert AuditEvent.objects.filter(action="auth.reset_issued", target_id=str(laura.pk)).exists()


# ---------- contraseña fuerte para roles sensibles ----------
def test_rol_sensible_no_acepta_pin(api, staff):
    tesorero = User.objects.create_user(
        "55 7777 8888", nombre="Tesorero", requires_strong_credential=True
    )
    from . import services

    raw, _ = services.issue_token(tesorero, ActivationToken.Purpose.ACTIVATION)
    r = api.post("/api/auth/activation/complete/", {"token": raw, "credential": PIN}, format="json")
    assert r.status_code == 400
    r = api.post(
        "/api/auth/activation/complete/",
        {"token": raw, "credential": "Alabanza-2026"},
        format="json",
    )
    assert r.status_code == 200


# ---------- cambio de número ----------
def test_cambio_de_numero_con_pin(api, laura):
    api.force_authenticate(laura)
    r = api.post(
        "/api/auth/me/whatsapp/", {"whatsapp": "55 2222 3333", "credential": PIN}, format="json"
    )
    assert r.status_code == 200 and r.json()["whatsapp"] == "+525522223333"
    evento = AuditEvent.objects.get(action="auth.whatsapp_changed")
    assert evento.detail == {"old": "+525511112222", "new": "+525522223333"}
    assert login(APIClient(), "5522223333").status_code == 200
    assert login(APIClient(), "5511112222").status_code == 400


def test_cambio_de_numero_exige_el_pin_correcto(api, laura):
    api.force_authenticate(laura)
    r = api.post(
        "/api/auth/me/whatsapp/", {"whatsapp": "5522223333", "credential": "000001"}, format="json"
    )
    assert r.status_code == 400
    laura.refresh_from_db()
    assert laura.whatsapp == "+525511112222"


def test_cambio_a_un_numero_ya_registrado(api, laura, staff):
    api.force_authenticate(laura)
    r = api.post(
        "/api/auth/me/whatsapp/", {"whatsapp": staff.whatsapp, "credential": PIN}, format="json"
    )
    assert r.status_code == 409 and r.json()["code"] == "duplicate"


# ---------- recuperación por correo ----------
def test_recuperacion_por_correo(api, laura):
    r = api.post("/api/auth/recovery/", {"identifier": "laura@example.com"}, format="json")
    assert r.status_code == 202
    assert len(mail.outbox) == 1 and "/activar/" in mail.outbox[0].body


def test_recuperacion_no_revela_si_la_cuenta_existe(api, laura):
    r1 = api.post("/api/auth/recovery/", {"identifier": "nadie@example.com"}, format="json")
    r2 = api.post("/api/auth/recovery/", {"identifier": "laura@example.com"}, format="json")
    assert r1.status_code == r2.status_code == 202 and r1.json() == r2.json()
    assert len(mail.outbox) == 1


# ---------- bitácora ----------
def test_la_bitacora_es_de_solo_anadir(laura):
    login_evento = AuditEvent.objects.create(action="prueba")
    login_evento.action = "otra"
    with pytest.raises(AppendOnlyError):
        login_evento.save()
    with pytest.raises(AppendOnlyError):
        login_evento.delete()
    with pytest.raises(AppendOnlyError):
        AuditEvent.objects.all().delete()
    with pytest.raises(AppendOnlyError):
        AuditEvent.objects.all().update(action="x")


# ---------- consola ----------
def test_createsuperuser_guarda_la_credencial_con_hash(db, monkeypatch):
    from django.core.management import call_command

    monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "Alabanza-2026")
    call_command(
        "createsuperuser", interactive=False, whatsapp="55 0000 0001", nombre="Admin", verbosity=0
    )
    user = User.objects.get(whatsapp="+525500000001")
    assert user.password.startswith("argon2$")
    assert user.is_staff and user.is_superuser and user.requires_strong_credential
    assert user.check_password("Alabanza-2026")


# ---------- CSRF con el frontend en otro origen (desarrollo con Vite) ----------
def test_peticion_autenticada_desde_el_origen_del_frontend(laura):
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(laura)
    token = client.get("/api/auth/csrf/").json()["csrfToken"]
    r = client.post(
        "/api/auth/logout/",
        HTTP_ORIGIN="http://localhost:5173",
        HTTP_HOST="localhost:8000",
        HTTP_X_CSRFTOKEN=token,
    )
    assert r.status_code == 204
