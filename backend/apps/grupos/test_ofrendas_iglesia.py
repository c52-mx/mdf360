from datetime import timedelta

import pytest
from django.core.cache import cache
from django.utils import timezone

from apps.core.models import AuditEvent

from .models import Grupo, GrupoMiembro, Ofrenda, OfrendaIglesia, Reunion, TipoOfrenda
from .test_ofrendas import FUERTE, api_de, cuenta


@pytest.fixture(autouse=True)
def _limpiar():
    cache.clear()


@pytest.fixture
def m(db):
    grupo = Grupo.objects.create(nombre="Conexión Norte")
    gente = dict(
        pastor=cuenta("55 0000 0001", "Pastor", "pastor", credencial=FUERTE),
        secretaria=cuenta("55 0000 0002", "Secretaria", "secretaria", credencial=FUERTE),
        tesorero=cuenta("55 0000 0003", "Tesorero", "tesorero", credencial=FUERTE),
        asistente=cuenta("55 0000 0004", "Asistente", "miembro"),
        secre_grupo=cuenta("55 0000 0005", "Secretario de grupo", "secretario"),
    )
    GrupoMiembro.objects.create(grupo=grupo, persona=gente["secre_grupo"].persona, rol="secretario")
    reunion = Reunion.objects.create(grupo=grupo, fecha=timezone.localdate())
    return {**gente, "grupo": grupo, "reunion": reunion}


def diezmo():
    return TipoOfrenda.objects.get(nombre="Diezmo")


def captura(usuario, monto="500.00", **extra):
    return api_de(usuario).post(
        "/api/grupos/ofrendas/iglesia/",
        {"tipo": diezmo().pk, "monto": monto, **extra},
        format="json",
    )


# ---------- catálogo ----------
def test_el_catalogo_se_siembra_con_los_tipos_de_grupo_y_de_iglesia(db):
    nombres = set(TipoOfrenda.objects.values_list("nombre", flat=True))
    assert {"Ofrenda regular", "Ofrenda especial", "Diezmo"} <= nombres
    assert not TipoOfrenda.objects.get(nombre="Diezmo").para_grupo


def test_cada_lugar_ve_solo_sus_tipos(m):
    api = api_de(m["secretaria"])
    grupo = {t["nombre"] for t in api.get("/api/grupos/ofrendas/tipos/?para=grupo").json()["tipos"]}
    iglesia = {
        t["nombre"] for t in api.get("/api/grupos/ofrendas/tipos/?para=iglesia").json()["tipos"]
    }
    assert "Diezmo" not in grupo and "Diezmo" in iglesia
    assert "Ofrenda regular" in grupo and "Ofrenda regular" in iglesia


def test_pastor_y_secretaria_administran_el_catalogo(m):
    r = api_de(m["secretaria"]).post(
        "/api/grupos/ofrendas/tipos/",
        {"nombre": "Pro templo", "para_iglesia": True},
        format="json",
    )
    assert r.status_code == 201 and r.json()["para_iglesia"] and not r.json()["para_grupo"]
    r = api_de(m["pastor"]).patch(
        f"/api/grupos/ofrendas/tipos/{r.json()['id']}/", {"activo": False}, format="json"
    )
    assert r.status_code == 200 and r.json()["activo"] is False
    assert AuditEvent.objects.filter(action="ofrenda.tipo_creado").exists()


def test_el_tesorero_no_administra_el_catalogo(m):
    r = api_de(m["tesorero"]).post(
        "/api/grupos/ofrendas/tipos/", {"nombre": "X", "para_iglesia": True}, format="json"
    )
    assert r.status_code == 403


def test_el_catalogo_no_admite_repetidos_ni_tipos_sin_lugar(m):
    api = api_de(m["pastor"])
    assert (
        api.post(
            "/api/grupos/ofrendas/tipos/", {"nombre": "diezmo", "para_iglesia": True}, format="json"
        ).status_code
        == 400
    )
    assert (
        api.post(
            "/api/grupos/ofrendas/tipos/",
            {"nombre": "Nuevo", "para_iglesia": False, "para_grupo": False},
            format="json",
        ).status_code
        == 400
    )


def test_el_asistente_no_entra_al_catalogo(m):
    assert api_de(m["asistente"]).get("/api/grupos/ofrendas/tipos/").status_code == 403


def test_la_captura_de_grupo_queda_ligada_al_catalogo(m):
    r = api_de(m["pastor"]).post(
        f"/api/grupos/reuniones/{m['reunion'].pk}/ofrendas/",
        {"tipo": "regular", "monto": "100"},
        format="json",
    )
    assert r.status_code == 201
    assert Ofrenda.objects.get().tipo_ofrenda.nombre == "Ofrenda regular"


# ---------- captura de la iglesia ----------
@pytest.mark.parametrize("quien", ["pastor", "secretaria", "tesorero"])
def test_capturan_pastor_secretaria_y_tesoreria(m, quien):
    r = captura(m[quien])
    assert r.status_code == 201
    assert r.json()["estado"] == "pendiente" and r.json()["origen"] == "iglesia"
    assert AuditEvent.objects.filter(action="ofrenda_iglesia.capturada").exists()


@pytest.mark.parametrize("quien", ["asistente", "secre_grupo"])
def test_los_demas_no_capturan_las_de_la_iglesia(m, quien):
    assert captura(m[quien]).status_code == 403


def test_captura_con_tipo_solo_de_grupo_o_fecha_futura_se_rechaza(m):
    regular_de_grupo = TipoOfrenda.objects.create(nombre="Solo grupo", para_grupo=True)
    r = api_de(m["pastor"]).post(
        "/api/grupos/ofrendas/iglesia/",
        {"tipo": regular_de_grupo.pk, "monto": "10"},
        format="json",
    )
    assert r.status_code == 400
    manana = (timezone.localdate() + timedelta(days=1)).isoformat()
    assert captura(m["pastor"], fecha=manana).status_code == 400


@pytest.mark.parametrize("monto", ["0", "-5", "abc"])
def test_montos_invalidos_en_la_iglesia(m, monto):
    assert captura(m["pastor"], monto=monto).status_code == 400


# ---------- aval ----------
def test_nadie_avala_lo_que_capturo(m):
    oid = captura(m["tesorero"]).json()["id"]
    r = api_de(m["tesorero"]).post(
        f"/api/grupos/ofrendas/iglesia/{oid}/aval/",
        {"monto_contado": "500", "credential": FUERTE},
        format="json",
    )
    assert r.status_code == 403 and r.json()["code"] == "own_capture"


def test_el_tesorero_avala_con_pin_y_queda_avalada(m):
    oid = captura(m["secretaria"]).json()["id"]
    r = api_de(m["tesorero"]).post(
        f"/api/grupos/ofrendas/iglesia/{oid}/aval/",
        {"monto_contado": "500", "credential": FUERTE},
        format="json",
    )
    assert r.status_code == 200 and r.json()["estado"] == "avalada"
    assert AuditEvent.objects.filter(action="ofrenda_iglesia.avalada").exists()


def test_una_diferencia_se_registra(m):
    oid = captura(m["secretaria"]).json()["id"]
    r = api_de(m["tesorero"]).post(
        f"/api/grupos/ofrendas/iglesia/{oid}/aval/",
        {"monto_contado": "450", "credential": FUERTE},
        format="json",
    )
    assert r.json()["estado"] == "diferencia"
    assert r.json()["movimientos"][-1]["diferencia"] == "-50.00"


def test_el_aval_con_pin_incorrecto_se_rechaza(m):
    oid = captura(m["secretaria"]).json()["id"]
    r = api_de(m["tesorero"]).post(
        f"/api/grupos/ofrendas/iglesia/{oid}/aval/",
        {"monto_contado": "500", "credential": "otra-cosa"},
        format="json",
    )
    assert r.status_code == 400 and r.json()["code"] == "invalid_pin"
    assert OfrendaIglesia.objects.get().estado == "pendiente"


def test_corregir_exige_motivo_y_pide_nuevo_aval(m):
    oid = captura(m["secretaria"]).json()["id"]
    api_de(m["tesorero"]).post(
        f"/api/grupos/ofrendas/iglesia/{oid}/aval/",
        {"monto_contado": "500", "credential": FUERTE},
        format="json",
    )
    sin = api_de(m["secretaria"]).patch(
        f"/api/grupos/ofrendas/iglesia/{oid}/", {"monto": "600", "motivo": " "}, format="json"
    )
    assert sin.status_code == 400
    r = api_de(m["secretaria"]).patch(
        f"/api/grupos/ofrendas/iglesia/{oid}/",
        {"monto": "600", "motivo": "Se contó mal"},
        format="json",
    )
    assert r.status_code == 200 and r.json()["estado"] == "pendiente"


def test_pendientes_incluyen_las_de_la_iglesia_menos_las_propias(m):
    captura(m["secretaria"])
    captura(m["tesorero"], monto="70")
    lista = api_de(m["tesorero"]).get("/api/grupos/ofrendas/pendientes/").json()
    assert [(o["origen"], o["monto"]) for o in lista] == [("iglesia", "500.00")]


# ---------- quién ve qué ----------
def test_nadie_ve_lo_de_otros_salvo_pastor_y_secretaria(m):
    oid = captura(m["secretaria"]).json()["id"]
    sin_ver = cuenta("55 0000 0009", "Otra tesorera", "tesorero", credencial=FUERTE)
    # quien puede avalar (Tesorería) ve también lo ya avalado
    api_de(m["tesorero"]).post(
        f"/api/grupos/ofrendas/iglesia/{oid}/aval/",
        {"monto_contado": "500", "credential": FUERTE},
        format="json",
    )
    assert api_de(sin_ver).get(f"/api/grupos/ofrendas/iglesia/{oid}/").status_code == 200
    assert api_de(m["asistente"]).get(f"/api/grupos/ofrendas/iglesia/{oid}/").status_code == 404
    assert api_de(m["pastor"]).get(f"/api/grupos/ofrendas/iglesia/{oid}/").status_code == 200
    assert api_de(m["secretaria"]).get(f"/api/grupos/ofrendas/iglesia/{oid}/").status_code == 200


def test_el_asistente_no_consulta_nada(m):
    api = api_de(m["asistente"])
    assert api.get("/api/grupos/ofrendas/iglesia/").status_code == 403
    assert api.get("/api/grupos/ofrendas/resumen/").status_code == 403


# ---------- resumen ----------
def _datos_de_resumen(m):
    captura(m["pastor"], monto="1000")
    hoy = timezone.localdate()
    api_de(m["pastor"]).post(
        f"/api/grupos/reuniones/{m['reunion'].pk}/ofrendas/",
        {"tipo": "regular", "monto": "250"},
        format="json",
    )
    return hoy


def test_el_resumen_junta_grupos_e_iglesia_con_totales(m):
    _datos_de_resumen(m)
    r = api_de(m["pastor"]).get("/api/grupos/ofrendas/resumen/").json()
    assert r["totales"]["total"] == "1250.00"
    assert r["totales"]["iglesia"] == "1000.00" and r["totales"]["grupo"] == "250.00"
    assert {f["origen"] for f in r["filas"]} == {"grupo", "iglesia"}
    assert sum(float(x["iglesia"]) + float(x["grupo"]) for x in r["por_mes"]) == 1250
    assert {t["tipo"] for t in r["por_tipo"]} == {"Diezmo", "Ofrenda regular"}


def test_el_resumen_filtra_por_origen_tipo_y_fechas(m):
    _datos_de_resumen(m)
    api = api_de(m["pastor"])
    assert (
        api.get("/api/grupos/ofrendas/resumen/?origen=iglesia").json()["totales"]["total"]
        == "1000.00"
    )
    assert (
        api.get("/api/grupos/ofrendas/resumen/?origen=grupo").json()["totales"]["total"] == "250.00"
    )
    tipo = diezmo().pk
    assert api.get(f"/api/grupos/ofrendas/resumen/?tipo={tipo}").json()["totales"]["cantidad"] == 1
    futuro = (timezone.localdate() + timedelta(days=30)).isoformat()
    assert api.get(f"/api/grupos/ofrendas/resumen/?desde={futuro}").json()["filas"] == []
    assert api.get("/api/grupos/ofrendas/resumen/?origen=otro").status_code == 400
    assert api.get("/api/grupos/ofrendas/resumen/?desde=hoy").status_code == 400


def test_quien_captura_ve_en_su_resumen_solo_lo_suyo(m):
    captura(m["secretaria"], monto="300")
    captura(m["pastor"], monto="900")
    r = api_de(m["secretaria"]).get("/api/grupos/ofrendas/resumen/").json()
    # la Secretaria tiene ver_todas, como el Pastor
    assert r["totales"]["total"] == "1200.00"
    r = api_de(m["tesorero"]).get("/api/grupos/ofrendas/resumen/").json()
    # el Tesorero ve todo lo de la iglesia
    assert r["totales"]["total"] == "1200.00"
    oid = OfrendaIglesia.objects.get(monto="300").pk
    api_de(m["tesorero"]).post(
        f"/api/grupos/ofrendas/iglesia/{oid}/aval/",
        {"monto_contado": "300", "credential": FUERTE},
        format="json",
    )
    r = api_de(m["tesorero"]).get("/api/grupos/ofrendas/resumen/").json()
    assert r["totales"]["total"] == "1200.00"  # Tesorería sigue viendo lo ya avalado
    assert r["totales"]["avalado"] == "300.00"


def test_el_secretario_de_grupo_ve_en_el_resumen_solo_su_grupo(m):
    api_de(m["secre_grupo"]).post(
        f"/api/grupos/reuniones/{m['reunion'].pk}/ofrendas/",
        {"tipo": "regular", "monto": "80"},
        format="json",
    )
    captura(m["pastor"], monto="1000")
    # el rol de grupo «secretario» captura pero no consulta, salvo el mismo día
    r = api_de(m["secre_grupo"]).get("/api/grupos/ofrendas/resumen/").json()
    assert r["totales"]["iglesia"] == "0"
    assert {f["origen"] for f in r["filas"]} <= {"grupo"}
