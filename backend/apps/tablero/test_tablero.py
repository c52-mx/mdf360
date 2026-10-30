from datetime import timedelta

import pytest
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import AsignacionRol, Rol, User
from apps.core.models import AuditEvent
from apps.grupos.models import Grupo, GrupoMiembro
from apps.personas import services as personas

from . import registry, services
from .models import Mensaje

PIN = "482915"


@pytest.fixture(autouse=True)
def _limpiar():
    cache.clear()


def cuenta(whatsapp, nombre, *roles):
    user = User.objects.create_user(whatsapp, nombre=nombre)
    user.set_password(PIN)
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
    norte = Grupo.objects.create(nombre="Conexión Norte")
    sur = Grupo.objects.create(nombre="Conexión Sur")
    g = dict(
        pastor=cuenta("55 0000 0001", "Pastor", "pastor"),
        anciano=cuenta("55 0000 0002", "Anciano", "anciano"),
        lider=cuenta("55 0000 0003", "Laura Líder", "lider"),
        secre=cuenta("55 0000 0004", "Sara Secretaria", "secretario"),
        sup=cuenta("55 0000 0005", "Samuel Supervisor", "supervisor"),
        asistente=cuenta("55 0000 0006", "Ana Asistente", "miembro"),
        tesorero=cuenta("55 0000 0007", "Tere Tesorera", "tesorero"),
        otro=cuenta("55 0000 0008", "Olga de otro grupo", "miembro"),
    )
    for clave, grupo, rol in (
        ("lider", norte, "lider"), ("secre", norte, "secretario"), ("sup", norte, "supervisor"),
        ("asistente", norte, "asistente"), ("tesorero", norte, "tesorero"), ("otro", sur, "asistente"),
    ):  # fmt: skip
        GrupoMiembro.objects.create(grupo=grupo, persona=g[clave].persona, rol=rol)
    return {**g, "norte": norte, "sur": sur}


def publicar(m, quien="lider", texto="Reunión este jueves a las 7:30", grupo="norte", **extra):
    return api_de(m[quien]).post(
        "/api/tablero/",
        {"origen_tipo": "grupo", "origen_id": m[grupo].pk, "texto": texto, **extra},
        format="json",
    )


def leer(m, quien, grupo="norte"):
    return api_de(m[quien]).get(f"/api/tablero/?origen_tipo=grupo&origen_id={m[grupo].pk}")


# ---------- permisos ----------
def test_quien_publica(m):
    for quien in ("lider", "sup", "secre", "pastor", "asistente"):
        assert publicar(m, quien).status_code == 201, quien
    for quien in ("tesorero", "anciano", "otro"):
        assert publicar(m, quien).status_code == 403, quien


def test_quien_lee(m):
    publicar(m)
    for quien in ("lider", "sup", "secre", "asistente", "tesorero", "pastor", "anciano"):
        r = leer(m, quien)
        assert r.status_code == 200 and len(r.json()) == 1, quien
    assert leer(m, "otro").status_code == 404  # integrante de otro grupo
    assert APIClient().get("/api/tablero/?origen_tipo=grupo&origen_id=1").status_code == 403


def test_el_mensaje_conserva_origen_y_autor(m):
    r = publicar(m).json()
    assert r["origen"]["etiqueta"] == "Grupo de Conexión · Conexión Norte"
    assert r["autor"] == "Laura Líder" and r["es_mio"] is True


def test_validaciones(m):
    assert publicar(m, texto="   ").status_code == 400
    assert publicar(m, texto="x" * 1001).status_code == 400
    api = api_de(m["lider"])
    assert (
        api.post(
            "/api/tablero/", {"origen_tipo": "curso", "origen_id": 1, "texto": "x"}, format="json"
        ).status_code
        == 400
    )
    assert (
        api.post(
            "/api/tablero/",
            {"origen_tipo": "grupo", "origen_id": 9999, "texto": "x"},
            format="json",
        ).status_code
        == 403
    )
    assert api.get("/api/tablero/").status_code == 400


# ---------- fijar y borrar ----------
def test_fijar_y_orden(m):
    a = publicar(m, texto="Primero").json()["id"]
    publicar(m, texto="Segundo")
    api = api_de(m["lider"])
    assert api.patch(f"/api/tablero/{a}/", {"fijado": True}, format="json").json()["fijado"] is True
    textos = [x["texto"] for x in leer(m, "asistente").json()]
    assert textos == ["Primero", "Segundo"]  # el fijado va arriba aunque sea más viejo
    assert AuditEvent.objects.filter(action="tablero.fijado").exists()


def test_el_asistente_no_modera(m):
    a = publicar(m).json()["id"]
    api = api_de(m["asistente"])
    assert api.patch(f"/api/tablero/{a}/", {"fijado": True}, format="json").status_code == 403
    assert api.delete(f"/api/tablero/{a}/").status_code == 403
    assert leer(m, "asistente").json()[0]["puede_moderar"] is False


def test_borrar_es_logico_y_queda_en_bitacora(m):
    a = publicar(m).json()["id"]
    assert (
        api_de(m["sup"]).delete(f"/api/tablero/{a}/").status_code == 204
    )  # quien puede publicar modera
    assert leer(m, "lider").json() == []
    assert Mensaje.objects.get(pk=a).eliminado is True
    assert AuditEvent.objects.filter(action="tablero.eliminado").exists()
    assert api_de(m["lider"]).delete(f"/api/tablero/{a}/").status_code == 404


def test_otro_grupo_no_puede_moderar(m):
    a = publicar(m).json()["id"]
    assert api_de(m["otro"]).delete(f"/api/tablero/{a}/").status_code == 404


def test_la_bitacora_no_guarda_el_texto(m):
    publicar(m, texto="Texto que no debe estar en bitácora")
    assert not any("no debe estar" in str(e.detail) for e in AuditEvent.objects.all())
    assert AuditEvent.objects.filter(action="tablero.publicado").exists()


# ---------- no leídos ----------
def test_contador_de_no_leidos(m):
    publicar(m, texto="Uno")
    publicar(m, texto="Dos")
    publicar(m, "pastor", texto="Del pastor")
    api = api_de(m["asistente"])
    assert api.get("/api/tablero/no-leidos/").json() == {"grupo": {str(m["norte"].pk): 3}}
    assert api_de(m["lider"]).get("/api/tablero/no-leidos/").json() == {
        "grupo": {str(m["norte"].pk): 1}
    }  # los suyos no cuentan
    assert api_de(m["otro"]).get("/api/tablero/no-leidos/").json() == {}
    assert (
        api.post(
            "/api/tablero/visto/",
            {"origen_tipo": "grupo", "origen_id": m["norte"].pk},
            format="json",
        ).status_code
        == 204
    )
    assert api.get("/api/tablero/no-leidos/").json() == {}
    publicar(m, texto="Nuevo")
    assert api.get("/api/tablero/no-leidos/").json() == {"grupo": {str(m["norte"].pk): 1}}


def test_marcar_visto_exige_poder_leer(m):
    r = api_de(m["otro"]).post(
        "/api/tablero/visto/", {"origen_tipo": "grupo", "origen_id": m["norte"].pk}, format="json"
    )
    assert r.status_code == 404


# ---------- retención ----------
def test_los_mensajes_viejos_se_purgan_y_es_configurable(m):
    a = publicar(m).json()["id"]
    Mensaje.objects.filter(pk=a).update(creado_en=timezone.now() - timedelta(days=91))
    assert leer(m, "lider").json() == []
    assert Mensaje.objects.count() == 0
    b = publicar(m).json()["id"]
    Mensaje.objects.filter(pk=b).update(creado_en=timezone.now() - timedelta(days=10))
    api_de(m["pastor"]).patch("/api/config/tablero.dias_retencion/", {"valor": 7}, format="json")
    assert services.purgar_antiguos() == 1


def test_comando_de_purga(m):
    from django.core.management import call_command

    a = publicar(m).json()["id"]
    Mensaje.objects.filter(pk=a).update(creado_en=timezone.now() - timedelta(days=200))
    call_command("purgar_tablero", verbosity=0)
    assert Mensaje.objects.count() == 0


# ---------- reutilización ----------
def test_otro_modulo_puede_usar_el_tablero(m):
    registry.registrar(
        registry.Origen(
            tipo="curso",
            nombre="Curso",
            etiqueta=lambda i: f"Curso · {i}",
            puede_publicar=lambda u, i: u.pk == m["anciano"].pk,
            puede_leer=lambda u, i: True,
            ids_legibles=lambda u: [5],
        )
    )
    try:
        r = api_de(m["anciano"]).post(
            "/api/tablero/",
            {"origen_tipo": "curso", "origen_id": 5, "texto": "Bienvenidos"},
            format="json",
        )
        assert r.status_code == 201 and r.json()["origen"]["etiqueta"] == "Curso · 5"
        assert (
            api_de(m["asistente"]).get("/api/tablero/?origen_tipo=curso&origen_id=5").status_code
            == 200
        )
        assert api_de(m["asistente"]).get("/api/tablero/no-leidos/").json() == {"curso": {"5": 1}}
    finally:
        registry._ORIGENES.pop("curso", None)


def test_el_asistente_publica_en_su_grupo_pero_no_en_otro_ni_modera_lo_ajeno(m):
    assert publicar(m, "asistente").status_code == 201
    ajeno = publicar(m, "lider").json()["id"]
    api = api_de(m["asistente"])
    assert api.patch(f"/api/tablero/{ajeno}/", {"fijado": True}, format="json").status_code == 403
    assert api.delete(f"/api/tablero/{ajeno}/").status_code == 403
    en_sur = api.post(
        "/api/tablero/",
        {"origen_tipo": "grupo", "origen_id": m["sur"].pk, "texto": "Hola"},
        format="json",
    )
    assert en_sur.status_code in (403, 404)


# ---------- avisos a toda la iglesia: se autorizan ----------
def a_la_iglesia(m, quien, texto="Convivio de la iglesia"):
    return api_de(m[quien]).post(
        "/api/tablero/masivo/",
        {"texto": texto, "destinos": [{"tipo": "iglesia", "id": 1}]},
        format="json",
    )


def en_la_iglesia(m, quien):
    return api_de(m[quien]).get("/api/tablero/?origen_tipo=iglesia&origen_id=1").json()


def test_el_asistente_pide_un_aviso_a_toda_la_iglesia_y_queda_pendiente(m):
    r = a_la_iglesia(m, "asistente")
    assert r.status_code == 201
    assert r.json()["enviados"] == [] and len(r.json()["pendientes"]) == 1
    assert en_la_iglesia(m, "lider") == []  # nadie lo ve todavía
    destinos = api_de(m["asistente"]).get("/api/tablero/destinos/").json()
    iglesia = next(d for d in destinos if d["tipo"] == "iglesia")
    assert iglesia["requiere_autorizacion"] is True
    pastor = api_de(m["pastor"]).get("/api/tablero/destinos/").json()
    assert next(d for d in pastor if d["tipo"] == "iglesia")["requiere_autorizacion"] is False
    # y lo que el Pastor envía sí sale directo
    assert a_la_iglesia(m, "pastor").json()["enviados"]


def test_quien_no_participa_en_ningun_tablero_no_puede_ni_pedirlo(m):
    sin_grupo = cuenta("55 0000 0090", "Sin grupo", "miembro")
    m["sin_grupo"] = sin_grupo
    assert a_la_iglesia(m, "sin_grupo").json()["pendientes"] == []


@pytest.mark.parametrize("quien", ["pastor", "lider", "sup"])
def test_pastor_lider_y_supervisor_autorizan_y_el_aviso_sale(m, quien):
    a_la_iglesia(m, "asistente")
    por = api_de(m[quien]).get("/api/tablero/por-autorizar/").json()
    assert por["puede_autorizar"] is True and len(por["avisos"]) == 1
    aviso = por["avisos"][0]
    assert api_de(m[quien]).post(f"/api/tablero/{aviso['id']}/autorizar/").status_code == 200
    visto = en_la_iglesia(m, "otro")
    assert [x["texto"] for x in visto] == ["Convivio de la iglesia"]
    assert visto[0]["autor"] == "Ana Asistente"
    assert AuditEvent.objects.filter(action="tablero.autorizado").exists()


def test_un_aviso_rechazado_no_sale_y_su_autor_lo_sabe(m):
    a_la_iglesia(m, "asistente")
    aviso = api_de(m["pastor"]).get("/api/tablero/por-autorizar/").json()["avisos"][0]
    assert api_de(m["pastor"]).post(f"/api/tablero/{aviso['id']}/rechazar/").status_code == 200
    assert en_la_iglesia(m, "otro") == []
    propio = api_de(m["asistente"]).get("/api/tablero/por-autorizar/").json()
    assert [(x["estado"], x["puede_resolver"]) for x in propio["avisos"]] == [("rechazado", False)]
    # ya resuelto, no se puede volver a resolver
    assert api_de(m["pastor"]).post(f"/api/tablero/{aviso['id']}/autorizar/").status_code == 404


def test_nadie_autoriza_su_propio_aviso_ni_lo_hace_quien_no_tiene_autoridad(m):
    a_la_iglesia(m, "lider")  # el líder no publica directo a la iglesia: lo pide
    a_la_iglesia(m, "asistente", texto="Otro")
    pid = api_de(m["lider"]).get("/api/tablero/por-autorizar/").json()["avisos"]
    propio = next(x for x in pid if x["texto"] == "Convivio de la iglesia")
    assert propio["puede_resolver"] is False
    assert api_de(m["lider"]).post(f"/api/tablero/{propio['id']}/autorizar/").status_code == 403
    # el asistente ve solo lo suyo y no puede autorizar
    suyo = api_de(m["asistente"]).get("/api/tablero/por-autorizar/").json()
    assert suyo["puede_autorizar"] is False and [x["texto"] for x in suyo["avisos"]] == ["Otro"]
    propio_id = suyo["avisos"][0]["id"]
    assert api_de(m["asistente"]).post(f"/api/tablero/{propio_id}/autorizar/").status_code == 403
    # y un pendiente no se puede fijar ni borrar como si estuviera publicado
    assert api_de(m["pastor"]).delete(f"/api/tablero/{propio['id']}/").status_code == 404
