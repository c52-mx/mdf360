"""Diseñador de formularios: campos adicionales versionados para Persona y Grupo."""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import AsignacionRol, Rol, User
from apps.core.models import AuditEvent
from apps.grupos.models import Grupo, GrupoMiembro
from apps.personas import services as personas

from .models import Formulario

PIN = "482915"


def cuenta(whatsapp, nombre, *roles):
    user = User.objects.create_user(whatsapp, pin=PIN, nombre=nombre)
    for clave in roles:
        AsignacionRol.objects.create(usuario=user, rol=Rol.objects.get(clave=clave))
    personas.ensure_persona_for_user(user)
    return user


def api_de(user):
    cliente = APIClient()
    cliente.force_authenticate(user)
    return cliente


@pytest.fixture
def mundo(db):
    return {
        "pastor": cuenta("55 0000 0501", "Pastor", "pastor"),
        "admin": cuenta("55 0000 0502", "Admin", "admin_tecnico"),
        "lider": cuenta("55 0000 0503", "Laura Líder", "lider"),
        "ana": cuenta("55 0000 0504", "Ana Ruiz", "miembro"),
    }


def campo(clave, etiqueta, tipo="texto", **extra):
    return {"clave": clave, "etiqueta": etiqueta, "tipo": tipo, **extra}


def guardar(user, entidad, campos):
    return api_de(user).put(f"/api/formularios/{entidad}/", {"campos": campos}, format="json")


# ---------- diseñar ----------
def test_se_agrega_un_campo_a_persona_y_cada_cambio_es_una_version(mundo):
    assert api_de(mundo["lider"]).get("/api/formularios/persona/").json()["version"] == 0
    r = guardar(
        mundo["pastor"], "persona", [campo("talla", "Talla", "seleccion", opciones=["S", "M", "L"])]
    )
    assert r.status_code == 200 and r.json()["version"] == 1
    mas = [*r.json()["campos"], campo("apodo", "Apodo")]
    assert guardar(mundo["pastor"], "persona", mas).json()["version"] == 2
    assert (
        guardar(mundo["pastor"], "persona", mas).json()["version"] == 2
    )  # sin cambios no versiona
    assert Formulario.objects.filter(entidad="persona").count() == 2
    assert AuditEvent.objects.filter(action="formulario.guardado").count() == 2


def test_solo_quien_diseña_formularios_los_cambia(mundo):
    for quien in ("lider", "ana"):
        assert guardar(mundo[quien], "persona", [campo("x", "X")]).status_code == 403
    assert guardar(mundo["admin"], "persona", [campo("x", "X")]).status_code == 200
    assert api_de(mundo["pastor"]).get("/api/formularios/nada/").status_code == 404


def test_un_campo_nunca_se_borra_ni_cambia_de_tipo_solo_se_desactiva(mundo):
    r = guardar(
        mundo["pastor"], "persona", [campo("talla", "Talla"), campo("edad", "Edad", "numero")]
    )
    campos = r.json()["campos"]
    quitado = guardar(mundo["pastor"], "persona", campos[:1])
    assert quitado.status_code == 400 and "no se puede quitar" in quitado.json()["detail"]
    cambiado = [campos[0], {**campos[1], "tipo": "texto"}]
    assert guardar(mundo["pastor"], "persona", cambiado).status_code == 400
    desactivado = [campos[0], {**campos[1], "activo": False}]
    assert guardar(mundo["pastor"], "persona", desactivado).status_code == 200


def test_validaciones_del_diseño(mundo):
    for malo in (
        [campo("a b", "Mal clave")],
        [campo("x", "")],
        [campo("x", "X", "seleccion", opciones=["una"])],
        [campo("x", "X", "relacion")],
        [campo("x", "X"), campo("x", "Otra")],
        [campo("x", "X", "inventado")],
    ):
        assert guardar(mundo["pastor"], "persona", malo).status_code == 400


# ---------- responder ----------
def preparar(mundo):
    guardar(
        mundo["pastor"],
        "persona",
        [
            campo("talla", "Talla", "seleccion", opciones=["S", "M", "L"], reportable=True),
            campo("hijos", "Hijos", "numero"),
            campo("bautizo", "Bautizo", "fecha"),
            campo("tutor", "Persona de confianza", "relacion", objetivo="persona", reportable=True),
            campo("rfc", "Referencia", requerido=True),
        ],
    )


def test_se_guardan_las_respuestas_y_se_validan(mundo):
    preparar(mundo)
    ana = mundo["ana"].persona
    pastor = api_de(mundo["pastor"])
    url = f"/api/personas/{ana.pk}/"
    ok = pastor.patch(
        url,
        {"datos_extra": {"talla": "M", "hijos": "2", "bautizo": "2020-05-01", "rfc": "abc"}},
        format="json",
    )
    assert ok.status_code == 200
    assert ok.json()["datos_extra"] == {
        "talla": "M",
        "hijos": 2,
        "bautizo": "2020-05-01",
        "rfc": "abc",
    }
    for malo in (
        {"talla": "XL", "rfc": "x"},
        {"hijos": "muchos", "rfc": "x"},
        {"bautizo": "ayer", "rfc": "x"},
        {"tutor": 999999, "rfc": "x"},
        {"talla": "S"},  # falta el obligatorio
    ):
        assert pastor.patch(url, {"datos_extra": malo}, format="json").status_code == 400


def test_un_campo_desactivado_conserva_sus_respuestas(mundo):
    preparar(mundo)
    ana = mundo["ana"].persona
    pastor = api_de(mundo["pastor"])
    url = f"/api/personas/{ana.pk}/"
    pastor.patch(url, {"datos_extra": {"talla": "L", "rfc": "x"}}, format="json")
    campos = pastor.get("/api/formularios/persona/").json()["campos"]
    for c in campos:
        if c["clave"] == "talla":
            c["activo"] = False
    assert guardar(mundo["pastor"], "persona", campos).status_code == 200
    r = pastor.patch(url, {"datos_extra": {"talla": "S", "rfc": "y"}}, format="json")
    assert r.json()["datos_extra"]["talla"] == "L"  # no se tocó
    assert r.json()["datos_extra"]["rfc"] == "y"


def test_campo_de_relacion_guarda_el_id_y_el_reporte_lo_cruza_con_el_grupo(mundo):
    preparar(mundo)
    norte = Grupo.objects.create(nombre="Conexión Norte")
    laura = mundo["lider"].persona
    GrupoMiembro.objects.create(grupo=norte, persona=laura, rol="lider")
    ana = mundo["ana"].persona
    pastor = api_de(mundo["pastor"])
    r = pastor.patch(
        f"/api/personas/{ana.pk}/",
        {"datos_extra": {"tutor": laura.pk, "talla": "M", "rfc": "x"}},
        format="json",
    )
    assert r.json()["datos_extra"]["tutor"] == laura.pk
    assert r.json()["datos_extra_etiquetas"]["tutor"] == "Laura Líder"
    reporte = {f["clave"]: f for f in pastor.get("/api/formularios/persona/reporte/").json()}
    assert reporte["talla"]["valores"] == [{"valor": "M", "total": 1}]
    assert reporte["tutor"]["valores"] == [{"valor": "Laura Líder", "total": 1}]
    assert reporte["tutor"]["por_grupo"] == [{"grupo": "Conexión Norte", "total": 1}]
    assert "hijos" not in reporte  # solo los marcados como reportables
    assert api_de(mundo["ana"]).get("/api/formularios/persona/reporte/").status_code == 403


def test_el_alta_de_una_persona_pide_los_campos_obligatorios(mundo):
    preparar(mundo)
    cuerpo = {"nombre": "Nueva", "whatsapp": "55 0000 0599", "acepta_datos": True}
    sin = api_de(mundo["pastor"]).post("/api/personas/", cuerpo, format="json")
    assert sin.status_code == 400
    con = api_de(mundo["pastor"]).post(
        "/api/personas/", {**cuerpo, "datos_extra": {"rfc": "ok", "talla": "S"}}, format="json"
    )
    assert con.status_code == 201 and con.json()["datos_extra"] == {"rfc": "ok", "talla": "S"}


def test_campos_adicionales_en_grupos(mundo):
    guardar(mundo["pastor"], "grupo", [campo("cupo", "Cupo", "numero", reportable=True)])
    r = api_de(mundo["pastor"]).post(
        "/api/grupos/", {"nombre": "Sur", "datos_extra": {"cupo": 12}}, format="json"
    )
    assert r.status_code == 201
    detalle = api_de(mundo["pastor"]).get(f"/api/grupos/{r.json()['id']}/").json()
    assert detalle["datos_extra"] == {"cupo": 12}
    cambio = api_de(mundo["pastor"]).patch(
        f"/api/grupos/{r.json()['id']}/", {"datos_extra": {"cupo": "x"}}, format="json"
    )
    assert cambio.status_code == 400
    rep = api_de(mundo["pastor"]).get("/api/formularios/grupo/reporte/").json()
    assert rep[0]["valores"] == [{"valor": "12", "total": 1}]
