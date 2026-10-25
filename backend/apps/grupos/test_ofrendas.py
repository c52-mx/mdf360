from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.models import AsignacionRol, Rol, User
from apps.core.models import AuditEvent
from apps.personas import services as personas

from .models import Grupo, GrupoMiembro, Ofrenda, Reunion

PIN = "482915"
FUERTE = "Tesoro-2026-x"


@pytest.fixture(autouse=True)
def _limpiar():
    cache.clear()


def cuenta(whatsapp, nombre, *roles, credencial=PIN):
    user = User.objects.create_user(whatsapp, nombre=nombre)
    user.set_password(credencial)  # directo: las contraseñas fuertes no pasan el validador de PIN
    user.save()
    for clave in roles:
        AsignacionRol.objects.create(usuario=user, rol=Rol.objects.get(clave=clave))
    personas.ensure_persona_for_user(user)
    return user


def api_de(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


@pytest.fixture
def m(db):
    grupo = Grupo.objects.create(nombre="Conexión Norte")
    otro = Grupo.objects.create(nombre="Conexión Sur")
    gente = dict(
        pastor=cuenta("55 0000 0001", "Pastor", "pastor", credencial=FUERTE),
        anciano=cuenta("55 0000 0002", "Anciano", "anciano"),
        lider=cuenta("55 0000 0003", "Líder", "lider"),
        secre=cuenta("55 0000 0004", "Secretaria", "secretario"),
        sup=cuenta("55 0000 0005", "Supervisor", "supervisor"),
        tesorero=cuenta("55 0000 0006", "Tesorero", "tesorero", credencial=FUERTE),
        ajeno=cuenta("55 0000 0007", "Tesorero ajeno", "tesorero", credencial=FUERTE),
    )
    for clave, rol in (("lider", "lider"), ("secre", "secretario"), ("sup", "supervisor"),
                       ("tesorero", "tesorero")):  # fmt: skip
        GrupoMiembro.objects.create(grupo=grupo, persona=gente[clave].persona, rol=rol)
    GrupoMiembro.objects.create(grupo=otro, persona=gente["ajeno"].persona, rol="tesorero")
    reunion = Reunion.objects.create(grupo=grupo, fecha=date.today())
    return {**gente, "grupo": grupo, "reunion": reunion}


def capturar(m, monto="1250.00", usuario="secre", **extra):
    return api_de(m[usuario]).post(
        f"/api/grupos/reuniones/{m['reunion'].pk}/ofrendas/",
        {"tipo": "regular", "monto": monto, **extra},
        format="json",
    )


# ---------- captura ----------
def test_el_secretario_captura_y_queda_pendiente(m):
    r = capturar(m)
    assert r.status_code == 201
    assert r.json()["estado"] == "pendiente" and r.json()["monto"] == "1250.00"
    assert r.json()["movimientos"][0]["tipo"] == "captura"
    assert AuditEvent.objects.filter(action="ofrenda.capturada").exists()


@pytest.mark.parametrize("quien", ["lider", "sup", "tesorero", "anciano"])
def test_nadie_mas_captura(m, quien):
    assert capturar(m, usuario=quien).status_code in (403, 404)


def test_el_pastor_puede_capturar_por_si_hace_falta(m):
    assert capturar(m, usuario="pastor").status_code == 201


def test_el_secretario_solo_captura_hoy(m):
    vieja = Reunion.objects.create(grupo=m["grupo"], fecha=date.today() - timedelta(days=7))
    r = api_de(m["secre"]).post(
        f"/api/grupos/reuniones/{vieja.pk}/ofrendas/", {"monto": "10"}, format="json"
    )
    assert r.status_code == 404  # tampoco la ve


@pytest.mark.parametrize("monto", ["0", "-5", "abc", "2000000"])
def test_montos_invalidos(m, monto):
    assert capturar(m, monto=monto).status_code == 400


def test_una_sola_regular_por_reunion_y_varias_especiales(m):
    assert capturar(m).status_code == 201
    assert capturar(m).status_code == 400
    r1 = api_de(m["secre"]).post(
        f"/api/grupos/reuniones/{m['reunion'].pk}/ofrendas/",
        {"tipo": "especial", "concepto": "Retiro", "monto": "300"}, format="json",
    )  # fmt: skip
    r2 = api_de(m["secre"]).post(
        f"/api/grupos/reuniones/{m['reunion'].pk}/ofrendas/",
        {"tipo": "especial", "concepto": "Despensas", "monto": "150"}, format="json",
    )  # fmt: skip
    sin = api_de(m["secre"]).post(
        f"/api/grupos/reuniones/{m['reunion'].pk}/ofrendas/",
        {"tipo": "especial", "monto": "150"}, format="json",
    )  # fmt: skip
    assert r1.status_code == r2.status_code == 201 and sin.status_code == 400


# ---------- confidencialidad (matriz) ----------
def test_quien_ve_las_ofrendas(m):
    capturar(m)
    url = f"/api/grupos/reuniones/{m['reunion'].pk}/ofrendas/"
    for quien in ("lider", "sup", "tesorero", "pastor", "secre"):
        assert api_de(m[quien]).get(url).status_code == 200, quien
    assert api_de(m["anciano"]).get(url).status_code == 404  # sin finanzas
    assert api_de(m["ajeno"]).get(url).status_code == 404  # tesorero de otro grupo


def test_el_lider_no_modifica_ni_avala(m):
    o = capturar(m).json()["id"]
    lider = api_de(m["lider"])
    assert (
        lider.patch(
            f"/api/grupos/ofrendas/{o}/", {"monto": "1", "motivo": "x"}, format="json"
        ).status_code
        == 403
    )
    assert (
        lider.post(
            f"/api/grupos/ofrendas/{o}/aval/",
            {"monto_contado": "1250", "credential": PIN},
            format="json",
        ).status_code
        == 404
    )


def test_consultar_ofrendas_queda_en_bitacora(m):
    api_de(m["lider"]).get(f"/api/grupos/reuniones/{m['reunion'].pk}/ofrendas/")
    assert AuditEvent.objects.filter(action="ofrenda.consultada").exists()


# ---------- aval ----------
def avalar(m, oid, contado, pin=FUERTE, usuario="tesorero"):
    return api_de(m[usuario]).post(
        f"/api/grupos/ofrendas/{oid}/aval/",
        {"monto_contado": contado, "credential": pin},
        format="json",
    )


def test_aval_que_coincide(m):
    o = capturar(m).json()["id"]
    r = avalar(m, o, "1250.00")
    assert r.status_code == 200 and r.json()["estado"] == "avalada"
    mov = r.json()["movimientos"][-1]
    assert mov["tipo"] == "aval" and Decimal(mov["diferencia"]) == 0 and mov["por"] == "Tesorero"
    assert AuditEvent.objects.filter(action="ofrenda.avalada").exists()


def test_aval_con_diferencia_registra_la_diferencia(m):
    o = capturar(m).json()["id"]
    r = avalar(m, o, "1200")
    assert r.json()["estado"] == "diferencia"
    assert Decimal(r.json()["movimientos"][-1]["diferencia"]) == Decimal("-50.00")
    evento = AuditEvent.objects.get(action="ofrenda.diferencia")
    assert evento.detail["diferencia"] == "-50.00"


def test_aval_exige_el_pin_correcto_y_bloquea(m, settings):
    o = capturar(m).json()["id"]
    for _ in range(settings.AUTH_LOCKOUT_ATTEMPTS):
        r = avalar(m, o, "1250", pin="incorrecta-123")
        assert r.status_code == 400 and r.json()["code"] == "invalid_pin"
    assert avalar(m, o, "1250").status_code == 429  # bloqueado aunque ahora sea correcto
    assert Ofrenda.objects.get(pk=o).estado == "pendiente"


def test_solo_el_tesorero_del_grupo_avala(m):
    o = capturar(m).json()["id"]
    for quien in ("ajeno", "pastor", "secre", "sup"):
        assert avalar(m, o, "1250", usuario=quien).status_code == 404, quien


def test_quien_capturo_no_se_avala_a_si_mismo(m):
    GrupoMiembro.objects.create(grupo=m["grupo"], persona=m["secre"].persona, rol="tesorero")
    o = capturar(m).json()["id"]
    r = api_de(m["secre"]).post(
        f"/api/grupos/ofrendas/{o}/aval/",
        {"monto_contado": "1250", "credential": PIN},
        format="json",
    )
    assert r.status_code == 403 and r.json()["code"] == "own_capture"


# ---------- corrección ----------
def test_corregir_exige_motivo_y_pide_nuevo_aval(m):
    o = capturar(m).json()["id"]
    avalar(m, o, "1250")
    api = api_de(m["secre"])
    assert (
        api.patch(
            f"/api/grupos/ofrendas/{o}/", {"monto": "1300", "motivo": ""}, format="json"
        ).status_code
        == 400
    )
    r = api.patch(
        f"/api/grupos/ofrendas/{o}/", {"monto": "1300", "motivo": "Se contó mal"}, format="json"
    )
    assert (
        r.status_code == 200
        and r.json()["estado"] == "pendiente"
        and r.json()["monto"] == "1300.00"
    )
    tipos = [x["tipo"] for x in r.json()["movimientos"]]
    assert tipos == ["captura", "aval", "correccion"]
    assert AuditEvent.objects.filter(action="ofrenda.corregida").exists()
    assert avalar(m, o, "1300").json()["estado"] == "avalada"


# ---------- pendientes del tesorero ----------
def test_pendientes_solo_de_sus_grupos(m):
    a = capturar(m).json()["id"]
    esp = api_de(m["secre"]).post(
        f"/api/grupos/reuniones/{m['reunion'].pk}/ofrendas/",
        {"tipo": "especial", "concepto": "Retiro", "monto": "300"}, format="json",
    ).json()["id"]  # fmt: skip
    avalar(m, a, "1250")
    pendientes = api_de(m["tesorero"]).get("/api/grupos/ofrendas/pendientes/").json()
    assert [p["id"] for p in pendientes] == [esp]
    assert api_de(m["ajeno"]).get("/api/grupos/ofrendas/pendientes/").json() == []
    assert api_de(m["lider"]).get("/api/grupos/ofrendas/pendientes/").json() == []


def test_permiso_de_finanzas_solo_para_el_pastor(db):
    assert "ofrendas.ver_todas" in Rol.objects.get(clave="pastor").permisos
    assert "ofrendas.ver_todas" not in Rol.objects.get(clave="anciano").permisos
