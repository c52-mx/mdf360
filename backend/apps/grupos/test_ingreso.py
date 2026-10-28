"""Ingreso por enlace o QR con aprobación del líder (sala de espera) y avisos de ingreso."""

import pytest
from django.core.cache import cache

from apps.accounts.models import AsignacionRol, Rol, User
from apps.core.models import AuditEvent
from apps.notificaciones import push

from .models import GrupoMiembro, SolicitudIngreso
from .test_grupos import api_de, cuenta, mundo  # noqa: F401  (fixture)


@pytest.fixture(autouse=True)
def _limpiar_cache():
    cache.clear()  # los límites de peticiones viven en la caché


DATOS = {"nombre": "Vecina Nueva", "whatsapp": "55 7000 0001", "acepta_datos": True}


def enlace_de(mundo_, quien="lider"):
    r = api_de(mundo_[quien]).post(f"/api/grupos/{mundo_['norte'].pk}/enlace/", {}, format="json")
    assert r.status_code == 201
    return r.json()["enlace"].rsplit("/", 1)[1]


def anonimo():
    from rest_framework.test import APIClient

    return APIClient()


# ---------- el enlace ----------
def test_solo_quien_gestiona_el_grupo_genera_el_enlace(mundo):
    url = f"/api/grupos/{mundo['norte'].pk}/enlace/"
    assert api_de(mundo["secre"]).post(url, {}, format="json").status_code == 403
    assert api_de(mundo["otro"]).post(url, {}, format="json").status_code == 404  # no es su grupo
    assert api_de(mundo["lider"]).post(url, {}, format="json").status_code == 201
    assert AuditEvent.objects.filter(action="grupo.enlace_generado").exists()


def test_regenerar_invalida_el_enlace_anterior_y_desactivar_lo_cierra(mundo):
    viejo = enlace_de(mundo)
    nuevo = enlace_de(mundo)
    assert viejo != nuevo
    assert anonimo().get(f"/api/grupos/enlace/{viejo}/").status_code == 404
    assert anonimo().get(f"/api/grupos/enlace/{nuevo}/").status_code == 200
    api_de(mundo["lider"]).delete(f"/api/grupos/{mundo['norte'].pk}/enlace/")
    assert anonimo().get(f"/api/grupos/enlace/{nuevo}/").status_code == 404


def test_la_pagina_publica_solo_muestra_nombre_y_horario(mundo):
    token = enlace_de(mundo)
    datos = anonimo().get(f"/api/grupos/enlace/{token}/").json()
    assert set(datos) == {"grupo", "dia", "hora"}
    assert datos["grupo"] == "Conexión Norte"


def test_un_grupo_suspendido_no_recibe_solicitudes(mundo):
    token = enlace_de(mundo)
    api_de(mundo["pastor"]).post(
        f"/api/grupos/{mundo['norte'].pk}/suspender/", {"motivo": "x"}, format="json"
    )
    assert (
        anonimo().post(f"/api/grupos/enlace/{token}/solicitar/", DATOS, format="json").status_code
        == 404
    )


def test_el_detalle_del_grupo_trae_el_enlace_solo_para_quien_lo_gestiona(mundo):
    token = enlace_de(mundo)
    url = f"/api/grupos/{mundo['norte'].pk}/"
    assert api_de(mundo["lider"]).get(url).json()["enlace"] == f"/unirse/{token}"
    assert api_de(mundo["secre"]).get(url).json()["enlace"] is None


# ---------- sala de espera ----------
def test_la_persona_espera_y_el_lider_la_aprueba(mundo):
    token = enlace_de(mundo)
    r = anonimo().post(f"/api/grupos/enlace/{token}/solicitar/", DATOS, format="json")
    assert r.status_code == 201 and r.json()["estado"] == "pendiente"
    codigo = r.json()["codigo"]
    assert anonimo().get(f"/api/grupos/solicitudes/{codigo}/").json()["estado"] == "pendiente"

    lider = api_de(mundo["lider"])
    pendientes = lider.get(f"/api/grupos/{mundo['norte'].pk}/solicitudes/").json()
    assert [p["nombre"] for p in pendientes] == ["Vecina Nueva"]
    # todavía no es integrante
    assert not GrupoMiembro.objects.filter(
        grupo=mundo["norte"], persona__nombre="Vecina Nueva"
    ).exists()

    ok = lider.post(f"/api/grupos/solicitudes/{pendientes[0]['id']}/aprobar/", {}, format="json")
    assert ok.status_code == 200 and ok.json()["estado"] == "aprobada"
    assert "wa.me" in ok.json()["whatsapp_url"]
    miembro = GrupoMiembro.objects.get(grupo=mundo["norte"], persona__nombre="Vecina Nueva")
    assert miembro.rol == "asistente" and miembro.activo
    assert anonimo().get(f"/api/grupos/solicitudes/{codigo}/").json()["estado"] == "aprobada"
    assert AuditEvent.objects.filter(action="grupo.solicitud_aprobada").exists()
    # no se resuelve dos veces
    assert (
        lider.post(
            f"/api/grupos/solicitudes/{pendientes[0]['id']}/aprobar/", {}, format="json"
        ).status_code
        == 400
    )


def test_el_lider_puede_rechazar(mundo):
    token = enlace_de(mundo)
    anonimo().post(f"/api/grupos/enlace/{token}/solicitar/", DATOS, format="json")
    sol = SolicitudIngreso.objects.get()
    r = api_de(mundo["lider"]).post(
        f"/api/grupos/solicitudes/{sol.pk}/rechazar/", {}, format="json"
    )
    assert r.json()["estado"] == "rechazada"
    assert not GrupoMiembro.objects.filter(
        grupo=mundo["norte"], persona__nombre="Vecina Nueva"
    ).exists()


def test_otro_lider_no_resuelve_solicitudes_ajenas(mundo):
    token = enlace_de(mundo)
    anonimo().post(f"/api/grupos/enlace/{token}/solicitar/", DATOS, format="json")
    sol = SolicitudIngreso.objects.get()
    assert (
        api_de(mundo["otro"])
        .post(f"/api/grupos/solicitudes/{sol.pk}/aprobar/", {}, format="json")
        .status_code
        == 404
    )
    assert (
        api_de(mundo["secre"])
        .post(f"/api/grupos/solicitudes/{sol.pk}/aprobar/", {}, format="json")
        .status_code
        == 403
    )
    assert (
        api_de(mundo["secre"]).get(f"/api/grupos/{mundo['norte'].pk}/solicitudes/").status_code
        == 403
    )


def test_pedir_dos_veces_devuelve_la_misma_solicitud(mundo):
    token = enlace_de(mundo)
    a = anonimo().post(f"/api/grupos/enlace/{token}/solicitar/", DATOS, format="json").json()
    b = anonimo().post(f"/api/grupos/enlace/{token}/solicitar/", DATOS, format="json").json()
    assert a["codigo"] == b["codigo"]
    assert SolicitudIngreso.objects.count() == 1


def test_exige_aviso_de_privacidad_nombre_y_whatsapp_valido(mundo):
    token = enlace_de(mundo)
    url = f"/api/grupos/enlace/{token}/solicitar/"
    assert anonimo().post(url, {**DATOS, "acepta_datos": False}, format="json").status_code == 400
    assert anonimo().post(url, {**DATOS, "nombre": "  "}, format="json").status_code == 400
    assert anonimo().post(url, {**DATOS, "whatsapp": "123"}, format="json").status_code == 400
    assert SolicitudIngreso.objects.count() == 0


def test_quien_ya_es_del_grupo_no_pide_ingreso(mundo):
    token = enlace_de(mundo)
    r = anonimo().post(
        f"/api/grupos/enlace/{token}/solicitar/",
        {**DATOS, "whatsapp": mundo["lider"].whatsapp},
        format="json",
    )
    assert r.status_code == 400 and "parte de este grupo" in r.json()["detail"]


def test_el_codigo_es_secreto_y_no_adivinable(mundo):
    assert anonimo().get("/api/grupos/solicitudes/no-existe/").status_code == 404


def test_las_solicitudes_publicas_tienen_limite_de_peticiones(mundo, settings):
    cache.clear()
    token = enlace_de(mundo)
    codigos = [anonimo().get(f"/api/grupos/enlace/{token}/").status_code for _ in range(25)]
    assert 429 in codigos


# ---------- avisos de ingreso ----------
def test_agregar_a_alguien_avisa_al_lider_y_a_la_persona(mundo, monkeypatch):
    avisos = []
    monkeypatch.setattr(push, "notificar", lambda **kw: avisos.append(kw) or 0)
    nueva = cuenta("55 0000 0060", "Nueva Cuenta", "miembro")
    r = api_de(mundo["pastor"]).post(
        f"/api/grupos/{mundo['norte'].pk}/integrantes/",
        {"whatsapp": nueva.whatsapp, "rol": "asistente"},
        format="json",
    )
    assert r.status_code == 201
    titulos = [a["titulo"] for a in avisos]
    assert "Nueva persona en Conexión Norte" in titulos
    assert "Te agregaron a un grupo" in titulos
    para_lideres = next(a for a in avisos if a["titulo"].startswith("Nueva persona"))
    assert mundo["lider"] in list(para_lideres["usuarios"])


def test_la_solicitud_avisa_a_los_lideres(mundo, monkeypatch):
    avisos = []
    monkeypatch.setattr(push, "notificar", lambda **kw: avisos.append(kw) or 0)
    token = enlace_de(mundo)
    anonimo().post(f"/api/grupos/enlace/{token}/solicitar/", DATOS, format="json")
    assert avisos and avisos[0]["titulo"] == "Quieren unirse a Conexión Norte"


# ---------- rol por defecto al invitar ----------
def test_quien_se_invita_queda_como_miembro(mundo):
    r = api_de(mundo["pastor"]).post(
        "/api/auth/invitations/",
        {"nombre": "Invitada Nueva", "whatsapp": "55 7000 0099"},
        format="json",
    )
    assert r.status_code == 201
    user = User.objects.get(whatsapp="+525570000099")
    assert user.roles_clave() == ["miembro"]
    assert AuditEvent.objects.filter(action="rbac.rol_por_defecto").exists()


def test_el_rol_por_defecto_no_pisa_los_que_ya_tiene(db):
    from apps.accounts import services

    user = User.objects.create_user("55 7000 0098", nombre="Con Rol")
    AsignacionRol.objects.create(usuario=user, rol=Rol.objects.get(clave="lider"))
    services.rol_por_defecto(user)
    assert user.roles_clave() == ["lider"]
