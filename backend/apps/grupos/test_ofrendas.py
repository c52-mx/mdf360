from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import AsignacionRol, Rol, RolEquipo, User
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
    reunion = Reunion.objects.create(grupo=grupo, fecha=timezone.localdate())
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
    vieja = Reunion.objects.create(grupo=m["grupo"], fecha=timezone.localdate() - timedelta(days=7))
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


# ---------- suplencias (el Líder suple al Secretario y al Tesorero) ----------
@pytest.fixture
def sin_cargos(m):
    GrupoMiembro.objects.filter(grupo=m["grupo"], rol__in=["secretario", "tesorero"]).update(
        activo=False
    )
    return m


def test_el_lider_captura_si_no_hay_secretario(sin_cargos):
    r = capturar(sin_cargos, usuario="lider")
    assert r.status_code == 201
    assert r.json()["movimientos"][0]["motivo"] == "Captura como suplente del Secretario"
    evento = AuditEvent.objects.get(action="ofrenda.capturada")
    assert evento.detail["suplencia"] is True


def test_el_lider_no_captura_si_hay_secretario(m):
    assert capturar(m, usuario="lider").status_code in (403, 404)


def test_sin_tesorero_avalan_el_pastor_o_el_lider_pero_no_quien_capturo(sin_cargos):
    o = capturar(sin_cargos, usuario="lider").json()["id"]
    propio = avalar(sin_cargos, o, "1250", pin=PIN, usuario="lider")
    assert propio.status_code == 403 and propio.json()["code"] == "own_capture"
    r = avalar(sin_cargos, o, "1250", pin=FUERTE, usuario="pastor")
    assert r.status_code == 200 and r.json()["estado"] == "avalada"
    assert r.json()["movimientos"][-1]["motivo"] == "Aval como suplente del Tesorero"
    assert AuditEvent.objects.filter(action="ofrenda.avalada", detail__suplencia=True).exists()


def test_con_secretario_pero_sin_tesorero_el_lider_avala(m):
    GrupoMiembro.objects.filter(grupo=m["grupo"], rol="tesorero").update(activo=False)
    o = capturar(m).json()["id"]
    r = avalar(m, o, "1250", pin=PIN, usuario="lider")
    assert r.status_code == 200 and r.json()["estado"] == "avalada"
    pend = capturar(m, tipo="especial", concepto="Retiro").json()["id"]
    assert pend in [
        p["id"] for p in api_de(m["lider"]).get("/api/grupos/ofrendas/pendientes/").json()
    ]


def test_con_tesorero_nadie_mas_avala(m):
    o = capturar(m).json()["id"]
    assert avalar(m, o, "1250", pin=PIN, usuario="lider").status_code == 404
    assert avalar(m, o, "1250", pin=FUERTE, usuario="pastor").status_code == 404


# ---------- diferencias visibles ----------
def test_las_diferencias_se_ven_en_el_grupo_para_quien_consulta(m):
    o = capturar(m).json()["id"]
    avalar(m, o, "1200")
    for quien in ("lider", "sup", "pastor"):
        grupos = api_de(m[quien]).get("/api/grupos/").json()
        norte = next(g for g in grupos if g["nombre"] == "Conexión Norte")
        assert norte["ofrendas_con_diferencia"] == 1, quien
    # el Tesorero la ve de inmediato en su pantalla de ofrendas
    pend = api_de(m["tesorero"]).get("/api/grupos/ofrendas/pendientes/").json()
    assert pend[0]["con_diferencia"] is True
    # el Anciano ve el grupo pero no las finanzas
    norte = next(
        g
        for g in api_de(m["anciano"]).get("/api/grupos/").json()
        if g["nombre"] == "Conexión Norte"
    )
    assert norte["ofrendas_con_diferencia"] is None
    detalle = api_de(m["lider"]).get(f"/api/grupos/{m['grupo'].pk}/").json()
    assert detalle["ofrendas_con_diferencia"] == 1
    assert (
        api_de(m["lider"])
        .get(f"/api/grupos/reuniones/{m['reunion'].pk}/ofrendas/")
        .json()["ofrendas"][0]["con_diferencia"]
    )


# ---------- parámetros configurables ----------
def test_monto_maximo_configurable(m):
    assert capturar(m, monto="2000000").status_code == 400
    api_de(m["pastor"]).patch(
        "/api/config/ofrendas.monto_maximo/", {"valor": 5000000}, format="json"
    )
    assert capturar(m, monto="2000000").status_code == 201
    api_de(m["pastor"]).patch("/api/config/ofrendas.monto_maximo/", {"valor": 500}, format="json")
    assert capturar(m, monto="600", tipo="especial", concepto="X").status_code == 400


def test_una_regular_por_reunion_configurable(m):
    assert capturar(m).status_code == 201
    assert capturar(m).status_code == 400
    api_de(m["pastor"]).patch(
        "/api/config/ofrendas.una_regular_por_reunion/", {"valor": False}, format="json"
    )
    assert capturar(m, monto="300").status_code == 201
    assert Ofrenda.objects.filter(reunion=m["reunion"], tipo="regular").count() == 2
    # las especiales con el mismo concepto siguen sin repetirse
    assert capturar(m, tipo="especial", concepto="Retiro").status_code == 201
    assert capturar(m, tipo="especial", concepto="Retiro").status_code == 400


def test_la_configuracion_exige_permiso_y_valida(m):
    assert api_de(m["lider"]).get("/api/config/").status_code == 403
    assert (
        api_de(m["anciano"])
        .patch("/api/config/ofrendas.monto_maximo/", {"valor": 1}, format="json")
        .status_code
        == 403
    )
    pastor = api_de(m["pastor"])
    lista = pastor.get("/api/config/").json()
    claves = {c["clave"] for c in lista}
    assert {"ofrendas.monto_maximo", "ofrendas.una_regular_por_reunion"} <= claves
    assert (
        pastor.patch("/api/config/ofrendas.monto_maximo/", {"valor": -1}, format="json").status_code
        == 400
    )
    assert (
        pastor.patch(
            "/api/config/ofrendas.monto_maximo/", {"valor": "abc"}, format="json"
        ).status_code
        == 400
    )
    assert (
        pastor.patch(
            "/api/config/ofrendas.una_regular_por_reunion/", {"valor": "si"}, format="json"
        ).status_code
        == 400
    )
    assert pastor.patch("/api/config/no.existe/", {"valor": 1}, format="json").status_code == 404
    ok = pastor.patch("/api/config/ofrendas.monto_maximo/", {"valor": 750000}, format="json")
    assert ok.status_code == 200
    evento = AuditEvent.objects.get(action="config.cambiada")
    assert evento.detail == {"clave": "ofrendas.monto_maximo", "anterior": 1000000, "nuevo": 750000}


def test_el_admin_tecnico_tambien_configura(db):
    admin = cuenta("55 0000 0050", "Admin", "admin_tecnico", credencial=FUERTE)
    assert api_de(admin).get("/api/config/").status_code == 200


# ---------- las reglas salen de los permisos del rol, no del nombre del rol ----------
def _dar(clave, *permisos, ambito="grupo"):
    rol = RolEquipo.objects.get(ambito=ambito, clave=clave)
    rol.permisos = sorted({*rol.permisos, *permisos})
    rol.save()


def _quitar(clave, *permisos, ambito="grupo"):
    rol = RolEquipo.objects.get(ambito=ambito, clave=clave)
    rol.permisos = sorted(set(rol.permisos) - set(permisos))
    rol.save()


def test_un_rol_nuevo_con_el_permiso_captura_y_otro_con_el_permiso_avala(m):
    cajero = RolEquipo.objects.create(
        ambito="grupo", clave="cajero", nombre="Cajero", permisos=["ofrendas_capturar"]
    )
    contador = RolEquipo.objects.create(
        ambito="grupo", clave="contador", nombre="Contador", permisos=["ofrendas_avalar"]
    )
    c = cuenta("55 0000 0010", "Cajero", "miembro")
    k = cuenta("55 0000 0011", "Contador", "miembro", credencial=FUERTE)
    GrupoMiembro.objects.create(grupo=m["grupo"], persona=c.persona, rol=cajero.clave)
    GrupoMiembro.objects.create(grupo=m["grupo"], persona=k.persona, rol=contador.clave)
    m.update(cajero=c, contador=k)
    # el cajero captura el mismo día (permiso del rol), aunque no sea Secretario
    r = capturar(m, usuario="cajero")
    assert r.status_code == 201
    # el contador avala con su PIN; quien no tiene el permiso, no
    oid = r.json()["id"]
    sin = api_de(m["sup"]).post(
        f"/api/grupos/ofrendas/{oid}/aval/",
        {"monto_contado": "1250.00", "credential": PIN},
        format="json",
    )
    assert sin.status_code == 404
    ok = api_de(k).post(
        f"/api/grupos/ofrendas/{oid}/aval/",
        {"monto_contado": "1250.00", "credential": FUERTE},
        format="json",
    )
    assert ok.status_code == 200 and ok.json()["estado"] == "avalada"


def test_quitar_el_permiso_al_secretario_le_quita_la_captura_y_la_suple_el_lider(m):
    _quitar("secretario", "ofrendas_capturar")
    assert capturar(m, usuario="secre").status_code == 404  # ni ve las ofrendas
    # ya nadie tiene el permiso principal en el grupo: el Líder entra como suplente
    r = capturar(m, usuario="lider")
    assert r.status_code == 201
    assert r.json()["movimientos"][0]["motivo"].startswith("Captura como suplente")


def test_si_se_quita_la_suplencia_el_lider_ya_no_captura_sin_secretario(m):
    GrupoMiembro.objects.filter(rol="secretario").update(activo=False)
    _quitar("lider", "ofrendas_capturar_suplente")
    assert capturar(m, usuario="lider").status_code == 403


def test_ver_las_ofrendas_es_un_permiso_del_rol(m):
    capturar(m)
    url = f"/api/grupos/reuniones/{m['reunion'].pk}/ofrendas/"
    assert api_de(m["sup"]).get(url).status_code == 200
    _quitar("supervisor", "ofrendas_ver")
    assert api_de(m["sup"]).get(url).status_code == 404
    _dar("anfitrion", "ofrendas_ver")
    anf = cuenta("55 0000 0012", "Anfitrión", "miembro")
    GrupoMiembro.objects.create(grupo=m["grupo"], persona=anf.persona, rol="anfitrion")
    assert api_de(anf).get(url).status_code == 200


def test_quien_capturo_nunca_avala_aunque_tenga_ambos_permisos(m):
    _dar("secretario", "ofrendas_avalar")
    r = capturar(m)
    oid = r.json()["id"]
    propio = api_de(m["secre"]).post(
        f"/api/grupos/ofrendas/{oid}/aval/",
        {"monto_contado": "1250.00", "credential": PIN},
        format="json",
    )
    assert propio.status_code == 403 and propio.json()["code"] == "own_capture"


# ---------- el módulo de Ofrendas solo existe para quien lo usa ----------
def test_el_asistente_no_tiene_ofrendas_ni_en_el_menu_ni_en_la_api(m):
    asistente = cuenta("55 0000 0097", "Ana Asistente", "miembro")
    GrupoMiembro.objects.create(grupo=m["grupo"], persona=asistente.persona, rol="asistente")
    api = api_de(asistente)
    assert "ofrendas.acceso" not in api.get("/api/auth/me/").json()["permisos"]
    assert api.get("/api/grupos/ofrendas/pendientes/").status_code == 403
    for quien in ("pastor", "tesorero", "secre"):
        permisos = api_de(m[quien]).get("/api/auth/me/").json()["permisos"]
        assert "ofrendas.acceso" in permisos, quien
