import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.models import AsignacionRol, Rol, User
from apps.core.models import AuditEvent
from apps.grupos.models import Grupo, GrupoMiembro
from apps.personas import services as personas
from apps.unidades.models import Unidad, UnidadMiembro

from .models import Publicacion

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
    cafe = Unidad.objects.create(nombre="Cafetería")
    g = dict(
        pastor=cuenta("55 0000 0001", "Pastor", "pastor"),
        lider=cuenta("55 0000 0003", "Laura Líder", "lider"),
        asistente=cuenta("55 0000 0006", "Ana Asistente", "miembro"),
        servidor=cuenta("55 0000 0007", "Saúl Servidor", "servidor"),
        otro=cuenta("55 0000 0008", "Olga de otro grupo", "miembro"),
    )
    for clave, grupo, rol in (
        ("lider", norte, "lider"),
        ("asistente", norte, "asistente"),
        ("otro", sur, "asistente"),
    ):
        GrupoMiembro.objects.create(grupo=grupo, persona=g[clave].persona, rol=rol)
    UnidadMiembro.objects.create(unidad=cafe, persona=g["servidor"].persona, rol="servidor")
    return {**g, "norte": norte, "sur": sur, "cafe": cafe}


def publicar(quien, texto, *destinos):
    return api_de(quien).post(
        "/api/muro/",
        {"texto": texto, "destinos": [{"tipo": t, "id": i} for t, i in destinos]},
        format="json",
    )


def textos(user, **params):
    r = api_de(user).get("/api/muro/", params)
    assert r.status_code == 200
    return [p["texto"] for p in r.json()["resultados"]]


def test_la_cena_navidena_llega_solo_a_cada_audiencia(m):
    # El ejemplo del pastor: público en general, servidores y un ministerio en concreto
    assert publicar(m["pastor"], "Cena para todos", ("iglesia", 1)).status_code == 201
    assert publicar(m["pastor"], "Cena para servidores", ("segmento", 1)).status_code == 201
    assert publicar(m["pastor"], "Cena para Cafetería", ("unidad", m["cafe"].pk)).status_code == 201

    assert textos(m["asistente"]) == ["Cena para todos"]
    assert set(textos(m["servidor"])) == {
        "Cena para todos",
        "Cena para servidores",
        "Cena para Cafetería",
    }
    assert textos(m["otro"]) == ["Cena para todos"]


def test_una_publicacion_con_varias_audiencias_aparece_una_sola_vez(m):
    r = publicar(m["pastor"], "Aviso doble", ("grupo", m["norte"].pk), ("segmento", 1))
    assert r.status_code == 201
    assert len(r.json()["audiencias"]) == 2
    assert textos(m["servidor"]) == ["Aviso doble"]
    assert textos(m["asistente"]) == ["Aviso doble"]
    assert textos(m["otro"]) == []


def test_publicar_en_el_grupo_pide_el_permiso_del_equipo(m):
    # El Asistente ya no publica por omisión; el líder sí
    r = publicar(m["asistente"], "Hola", ("grupo", m["norte"].pk))
    assert r.status_code == 403
    assert publicar(m["lider"], "Reunión el jueves", ("grupo", m["norte"].pk)).status_code == 201
    assert textos(m["asistente"]) == ["Reunión el jueves"]
    # …pero el líder no publica en el grupo de otros ni a toda la iglesia
    assert publicar(m["lider"], "x", ("grupo", m["sur"].pk)).status_code == 403
    assert publicar(m["lider"], "x", ("iglesia", 1)).status_code == 403


def test_si_falla_una_audiencia_no_se_crea_nada(m):
    r = publicar(m["lider"], "Mixto", ("grupo", m["norte"].pk), ("iglesia", 1))
    assert r.status_code == 403
    assert Publicacion.objects.count() == 0


def test_validaciones(m):
    assert publicar(m["pastor"], "  ", ("iglesia", 1)).status_code == 400
    assert publicar(m["pastor"], "Hola").status_code == 400  # sin audiencias
    assert publicar(m["pastor"], "Hola", ("curso", 1)).status_code == 400
    assert publicar(m["pastor"], "Hola", ("grupo", 9999)).status_code == 400
    assert publicar(m["pastor"], "Hola", ("segmento", 99)).status_code == 400


def test_destinos_segun_permisos(m):
    def tipos(user):
        return {(d["tipo"], d["id"]) for d in api_de(user).get("/api/muro/destinos/").json()}

    assert tipos(m["asistente"]) == set()
    assert tipos(m["lider"]) == {("grupo", m["norte"].pk)}
    pastoral = tipos(m["pastor"])
    assert {("iglesia", 1), ("segmento", 1), ("grupo", m["norte"].pk)} <= pastoral


def test_el_muro_pagina_y_filtra_por_audiencia(m):
    for i in range(25):
        publicar(m["pastor"], f"Aviso {i}", ("iglesia", 1))
    publicar(m["pastor"], "Solo norte", ("grupo", m["norte"].pk))
    r = api_de(m["asistente"]).get("/api/muro/").json()
    assert len(r["resultados"]) == 20
    assert r["resultados"][0]["texto"] == "Solo norte"  # lo más reciente primero
    assert r["siguiente"] is not None
    resto = api_de(m["asistente"]).get("/api/muro/", {"antes": r["siguiente"]}).json()
    assert len(resto["resultados"]) == 6
    assert resto["siguiente"] is None
    solo = textos(m["asistente"], audiencia_tipo="grupo", audiencia_id=m["norte"].pk)
    assert solo == ["Solo norte"]


def test_el_autor_ve_lo_suyo_y_hay_bitacora(m):
    publicar(m["lider"], "Mío", ("grupo", m["norte"].pk))
    assert textos(m["lider"]) == ["Mío"]
    assert AuditEvent.objects.filter(action="muro.publicado").count() == 1


def test_requiere_sesion(db):
    assert APIClient().get("/api/muro/").status_code in (401, 403)
    assert APIClient().post("/api/muro/", {}, format="json").status_code in (401, 403)


def test_avisos_ya_publicados_se_copian_al_muro(m):
    # La migración de datos copia lo publicado antes; aquí se prueba su función directamente
    import importlib

    from django.apps import apps as registro

    from apps.tablero.models import Mensaje

    Mensaje.objects.create(
        origen_tipo="grupo", origen_id=m["norte"].pk, origen_etiqueta="Grupo · Conexión Norte",
        autor=m["lider"], autor_nombre="Laura Líder", texto="Aviso viejo",
    )  # fmt: skip
    Mensaje.objects.create(
        origen_tipo="persona", origen_id=1, origen_etiqueta="Aviso personal",
        autor=m["pastor"], autor_nombre="Pastor", texto="Privado",
    )  # fmt: skip
    importlib.import_module("apps.muro.migrations.0002_copiar_avisos").copiar(registro, None)
    assert textos(m["asistente"]) == ["Aviso viejo"]
    assert not Publicacion.objects.filter(texto="Privado").exists()


# ---------- reacciones y comentarios (paso 24) ----------
def una(m, texto="Cena para servidores", *destinos):
    r = publicar(m["pastor"], texto, *(destinos or [("segmento", 1)]))
    assert r.status_code == 201
    return r.json()["id"]


def reaccionar(user, pid, tipo):
    return api_de(user).put(f"/api/muro/{pid}/reaccion/", {"tipo": tipo}, format="json")


def test_cualquiera_que_ve_la_publicacion_reacciona_y_cambia_o_quita(m):
    pid = una(m)
    r = reaccionar(m["servidor"], pid, "amen")
    assert r.status_code == 200
    assert r.json()["reacciones"] == {"amen": 1} and r.json()["mi_reaccion"] == "amen"
    # cambiar de reacción no suma otra
    assert reaccionar(m["servidor"], pid, "corazon").json()["reacciones"] == {"corazon": 1}
    # tocar la misma la quita
    quitada = reaccionar(m["servidor"], pid, "corazon").json()
    assert quitada["reacciones"] == {} and quitada["mi_reaccion"] is None
    assert reaccionar(m["servidor"], pid, "inventada").status_code == 400


def test_el_muro_trae_conteos_y_mi_reaccion(m):
    pid = una(m, "Para todos", ("iglesia", 1))
    reaccionar(m["asistente"], pid, "me_gusta")
    reaccionar(m["lider"], pid, "me_gusta")
    reaccionar(m["otro"], pid, "amen")
    api_de(m["otro"]).post(f"/api/muro/{pid}/comentarios/", {"texto": "Ahí estaré"}, format="json")
    fila = api_de(m["asistente"]).get("/api/muro/").json()["resultados"][0]
    assert fila["reacciones"] == {"me_gusta": 2, "amen": 1}
    assert fila["mi_reaccion"] == "me_gusta" and fila["comentarios_total"] == 1


def test_quien_no_ve_la_publicacion_no_reacciona_ni_comenta_ni_la_lee(m):
    pid = una(m)  # solo servidores
    assert reaccionar(m["asistente"], pid, "amen").status_code == 404
    c = api_de(m["asistente"])
    assert c.post(f"/api/muro/{pid}/comentarios/", {"texto": "x"}, format="json").status_code == 404
    assert c.get(f"/api/muro/{pid}/comentarios/").status_code == 404


def test_comentarios_se_leen_en_orden_y_se_validan(m):
    pid = una(m, "Para todos", ("iglesia", 1))
    a, s = api_de(m["asistente"]), api_de(m["servidor"])
    assert (
        a.post(f"/api/muro/{pid}/comentarios/", {"texto": "  "}, format="json").status_code == 400
    )
    assert (
        a.post(f"/api/muro/{pid}/comentarios/", {"texto": "x" * 501}, format="json").status_code
        == 400
    )
    a.post(f"/api/muro/{pid}/comentarios/", {"texto": "Primero"}, format="json")
    s.post(f"/api/muro/{pid}/comentarios/", {"texto": "Segundo"}, format="json")
    lista = s.get(f"/api/muro/{pid}/comentarios/").json()
    assert [c["texto"] for c in lista] == ["Primero", "Segundo"]
    assert [c["es_mio"] for c in lista] == [False, True]


def test_quitar_comentario_lo_hace_su_autor_o_el_de_la_publicacion(m):
    pid = una(m, "Para todos", ("iglesia", 1))
    cid = (
        api_de(m["asistente"])
        .post(f"/api/muro/{pid}/comentarios/", {"texto": "Hola"}, format="json")
        .json()["id"]
    )
    # otra persona que ve la publicación no puede quitarlo
    assert api_de(m["otro"]).delete(f"/api/muro/comentarios/{cid}/").status_code == 403
    # el autor de la publicación sí
    assert api_de(m["pastor"]).delete(f"/api/muro/comentarios/{cid}/").status_code == 204
    assert api_de(m["asistente"]).get(f"/api/muro/{pid}/comentarios/").json() == []
    c2 = (
        api_de(m["otro"])
        .post(f"/api/muro/{pid}/comentarios/", {"texto": "Otro"}, format="json")
        .json()["id"]
    )
    assert api_de(m["otro"]).delete(f"/api/muro/comentarios/{c2}/").status_code == 204
