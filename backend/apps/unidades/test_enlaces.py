"""QR fijo por grupo y por ministerio; el del ministerio suma sin aprobación como servidor."""

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.core.models import AuditEvent
from apps.grupos.models import Grupo, GrupoMiembro
from apps.personas.models import Persona

from .models import Unidad, UnidadMiembro
from .test_unidades import api_de, cuenta


@pytest.fixture(autouse=True)
def _limpiar():
    cache.clear()


@pytest.fixture
def m(db):
    pastor = cuenta("55 0000 0001", "Pastor", "pastor")
    encargada = cuenta("55 0000 0004", "Eva Encargada", "servidor")
    servidor = cuenta("55 0000 0006", "Sergio Servidor", "servidor")
    lider = cuenta("55 0000 0007", "Laura Líder", "lider")
    cafeteria = Unidad.objects.create(nombre="Cafetería", enlace_token="tok-cafe")
    UnidadMiembro.objects.create(unidad=cafeteria, persona=encargada.persona, rol="encargado")
    UnidadMiembro.objects.create(unidad=cafeteria, persona=servidor.persona, rol="servidor")
    grupo = Grupo.objects.create(nombre="Conexión Norte", enlace_token="tok-grupo")
    GrupoMiembro.objects.create(grupo=grupo, persona=lider.persona, rol="lider")
    return dict(
        pastor=pastor, encargada=encargada, servidor=servidor, lider=lider,
        cafeteria=cafeteria, grupo=grupo,
    )  # fmt: skip


def sumarse(token="tok-cafe", **extra):
    datos = {"nombre": "Nora Nueva", "whatsapp": "55 7777 0001", "acepta_datos": True, **extra}
    return APIClient().post(f"/api/unidades/enlace/{token}/sumarse/", datos, format="json")


# ---------- se crean con el grupo y el ministerio ----------
def test_al_crear_un_ministerio_ya_tiene_su_qr(m):
    r = api_de(m["pastor"]).post("/api/unidades/", {"nombre": "Danza"}, format="json")
    assert r.status_code == 201
    assert Unidad.objects.get(nombre="Danza").enlace_token


def test_al_crear_un_grupo_ya_tiene_su_qr(m):
    r = api_de(m["pastor"]).post(
        "/api/grupos/",
        {"nombre": "Conexión Sur", "dia_semana": 2, "hora": "19:00"},
        format="json",
    )
    assert r.status_code == 201
    assert Grupo.objects.get(nombre="Conexión Sur").enlace_token


# ---------- ingreso por el QR del ministerio ----------
def test_el_enlace_publico_solo_muestra_el_nombre(m):
    r = APIClient().get("/api/unidades/enlace/tok-cafe/")
    assert r.status_code == 200 and r.json() == {"ministerio": "Cafetería", "descripcion": ""}
    assert APIClient().get("/api/unidades/enlace/no-existe/").status_code == 404


def test_quien_abre_el_qr_entra_como_servidor_sin_aprobacion(m):
    r = sumarse()
    assert r.status_code == 201
    miembro = UnidadMiembro.objects.get(persona__whatsapp__contains="7777")
    assert miembro.rol == "servidor" and miembro.activo and miembro.unidad == m["cafeteria"]
    assert AuditEvent.objects.filter(action="unidad.ingreso_por_qr").exists()


def test_exige_aceptar_el_aviso_de_privacidad_si_es_nueva(m):
    assert sumarse(acepta_datos=False).status_code == 400
    assert not Persona.objects.filter(whatsapp__contains="7777").exists()


def test_quien_ya_existe_se_vincula_sin_duplicarse(m):
    antes = Persona.objects.count()
    r = sumarse(nombre="Sergio", whatsapp="55 0000 0006", acepta_datos=False)
    assert r.status_code == 201
    assert Persona.objects.count() == antes  # misma persona
    assert (
        UnidadMiembro.objects.filter(persona=m["servidor"].persona, unidad=m["cafeteria"]).count()
        == 1
    )


def test_sumarse_dos_veces_no_duplica(m):
    assert sumarse().status_code == 201
    assert sumarse().status_code == 201
    assert (
        UnidadMiembro.objects.filter(
            unidad=m["cafeteria"], persona__whatsapp__contains="7777"
        ).count()
        == 1
    )


def test_el_qr_no_da_roles_de_gestion(m):
    sumarse()
    assert not UnidadMiembro.objects.filter(
        rol__in=["encargado", "respaldo"], persona__whatsapp__contains="7777"
    )


def test_un_enlace_regenerado_o_un_ministerio_inactivo_no_sirven(m):
    api_de(m["pastor"]).post(f"/api/unidades/{m['cafeteria'].pk}/enlace/")
    assert sumarse().status_code == 404  # el token viejo ya no sirve
    nuevo = Unidad.objects.get(pk=m["cafeteria"].pk)
    nuevo.activa = False
    nuevo.save()
    assert sumarse(token=nuevo.enlace_token).status_code == 404


# ---------- gestión del enlace ----------
def test_el_encargado_regenera_y_desactiva(m):
    api = api_de(m["encargada"])
    r = api.post(f"/api/unidades/{m['cafeteria'].pk}/enlace/")
    assert r.status_code == 201 and r.json()["enlace"].startswith("/servir/")
    assert api.delete(f"/api/unidades/{m['cafeteria'].pk}/enlace/").status_code == 204
    assert Unidad.objects.get(pk=m["cafeteria"].pk).enlace_token is None
    assert AuditEvent.objects.filter(action="unidad.enlace_desactivado").exists()


def test_el_servidor_no_gestiona_ni_ve_el_enlace(m):
    api = api_de(m["servidor"])
    assert api.post(f"/api/unidades/{m['cafeteria'].pk}/enlace/").status_code == 403
    assert api.get(f"/api/unidades/{m['cafeteria'].pk}/").json()["enlace"] is None


def test_el_encargado_ve_el_enlace_en_el_detalle(m):
    r = api_de(m["encargada"]).get(f"/api/unidades/{m['cafeteria'].pk}/")
    assert r.json()["enlace"] == "/servir/tok-cafe"


# ---------- mis enlaces ----------
def test_mis_enlaces_junta_grupos_y_ministerios_que_gestionas(m):
    lista = api_de(m["pastor"]).get("/api/grupos/mis-enlaces/").json()
    assert {(f["tipo"], f["nombre"]) for f in lista} == {
        ("grupo", "Conexión Norte"),
        ("ministerio", "Cafetería"),
    }
    por_tipo = {f["tipo"]: f for f in lista}
    assert (
        por_tipo["grupo"]["requiere_aprobacion"]
        and not por_tipo["ministerio"]["requiere_aprobacion"]
    )
    assert por_tipo["ministerio"]["enlace"] == "/servir/tok-cafe"


def test_mis_enlaces_solo_trae_lo_que_gestiona_cada_quien(m):
    assert [f["nombre"] for f in api_de(m["lider"]).get("/api/grupos/mis-enlaces/").json()] == [
        "Conexión Norte"
    ]
    assert [f["nombre"] for f in api_de(m["encargada"]).get("/api/grupos/mis-enlaces/").json()] == [
        "Cafetería"
    ]
    assert api_de(m["servidor"]).get("/api/grupos/mis-enlaces/").json() == []
