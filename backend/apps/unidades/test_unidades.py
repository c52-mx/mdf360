"""Unidades (áreas de servicio) con alcance propio, y avisos masivos."""

import pytest
from django.core.cache import cache

from apps.accounts.models import AsignacionRol, Rol, User
from apps.core.models import AuditEvent
from apps.grupos.models import Grupo, GrupoMiembro
from apps.notificaciones import push
from apps.personas import services as personas
from apps.tablero.models import Mensaje

from .models import Unidad, UnidadMiembro

PIN = "482915"


@pytest.fixture(autouse=True)
def _limpiar():
    cache.clear()


def cuenta(whatsapp, nombre, *roles):
    user = User.objects.create_user(whatsapp, pin=PIN, nombre=nombre)
    for clave in roles:
        AsignacionRol.objects.create(usuario=user, rol=Rol.objects.get(clave=clave))
    personas.ensure_persona_for_user(user)
    return user


def api_de(user):
    from rest_framework.test import APIClient

    c = APIClient()
    c.force_authenticate(user)
    return c


@pytest.fixture
def mundo(db):
    pastor = cuenta("55 0000 0001", "Pastor", "pastor")
    secretaria = cuenta("55 0000 0002", "Secretaria", "secretaria")
    anciano = cuenta("55 0000 0003", "Anciano", "anciano")
    encargada = cuenta("55 0000 0004", "Eva Encargada", "servidor")
    respaldo = cuenta("55 0000 0005", "Rita Respaldo", "servidor")
    servidor = cuenta("55 0000 0006", "Sergio Servidor", "servidor")
    lider = cuenta("55 0000 0007", "Laura Líder", "lider")
    ajena = cuenta("55 0000 0008", "Ana Ajena", "miembro")
    cafeteria = Unidad.objects.create(nombre="Cafetería")
    libreria = Unidad.objects.create(nombre="Librería")
    for u, user, rol in (
        (cafeteria, encargada, "encargado"),
        (cafeteria, respaldo, "respaldo"),
        (cafeteria, servidor, "servidor"),
        (libreria, encargada, "servidor"),  # sirve en otra unidad con otro rol
    ):
        UnidadMiembro.objects.create(unidad=u, persona=user.persona, rol=rol)
    norte = Grupo.objects.create(nombre="Conexión Norte")
    GrupoMiembro.objects.create(grupo=norte, persona=lider.persona, rol="lider")
    GrupoMiembro.objects.create(grupo=norte, persona=encargada.persona, rol="asistente")
    return dict(
        pastor=pastor, secretaria=secretaria, anciano=anciano, encargada=encargada,
        respaldo=respaldo, servidor=servidor, lider=lider, ajena=ajena,
        cafeteria=cafeteria, libreria=libreria, norte=norte,
    )  # fmt: skip


# ---------- alcance por unidad ----------
def test_cada_quien_ve_solo_sus_unidades(mundo):
    nombres = lambda u: sorted(x["nombre"] for x in api_de(u).get("/api/unidades/").json())  # noqa: E731
    assert nombres(mundo["encargada"]) == ["Cafetería", "Librería"]
    assert nombres(mundo["servidor"]) == ["Cafetería"]
    assert nombres(mundo["lider"]) == []  # liderar un grupo no da acceso a ninguna unidad
    assert nombres(mundo["ajena"]) == []
    assert nombres(mundo["pastor"]) == nombres(mundo["anciano"]) == ["Cafetería", "Librería"]


def test_el_alcance_de_cada_rol_es_independiente_por_unidad(mundo):
    encargada = api_de(mundo["encargada"])
    caf = encargada.get(f"/api/unidades/{mundo['cafeteria'].pk}/").json()
    lib = encargada.get(f"/api/unidades/{mundo['libreria'].pk}/").json()
    assert caf["puede_gestionar"] is True  # encargada en la cafetería
    assert lib["puede_gestionar"] is False  # solo servidora en la librería
    assert lib["mis_roles"] == ["servidor"]
    # como asistente de un grupo no administra nada de él: ve solo su tablero de avisos
    assert api_de(mundo["encargada"]).get(f"/api/grupos/{mundo['norte'].pk}/").status_code == 404
    avisos = api_de(mundo["encargada"]).get("/api/tablero/mis-tableros/").json()
    grupo = next(t for t in avisos if t["tipo"] == "grupo")
    assert grupo["puede_publicar"] is False


def test_una_unidad_ajena_no_existe_para_quien_no_participa(mundo):
    assert (
        api_de(mundo["servidor"]).get(f"/api/unidades/{mundo['libreria'].pk}/").status_code == 404
    )
    assert api_de(mundo["lider"]).get(f"/api/unidades/{mundo['cafeteria'].pk}/").status_code == 404


def test_solo_la_administracion_crea_y_edita_unidades(mundo):
    datos = {"nombre": "Danza", "descripcion": "Ministerio de danza"}
    assert (
        api_de(mundo["encargada"]).post("/api/unidades/", datos, format="json").status_code == 403
    )
    assert api_de(mundo["anciano"]).post("/api/unidades/", datos, format="json").status_code == 403
    for quien in ("pastor", "secretaria"):
        nombre = {"pastor": "Danza", "secretaria": "Niños"}[quien]
        r = api_de(mundo[quien]).post("/api/unidades/", {**datos, "nombre": nombre}, format="json")
        assert r.status_code == 201
    repetida = api_de(mundo["pastor"]).post("/api/unidades/", datos, format="json")
    assert repetida.status_code == 400
    url = f"/api/unidades/{mundo['cafeteria'].pk}/"
    assert api_de(mundo["encargada"]).patch(url, {"nombre": "X"}, format="json").status_code == 403
    assert (
        api_de(mundo["pastor"]).patch(url, {"descripcion": "Café y pan"}, format="json").status_code
        == 200
    )
    assert AuditEvent.objects.filter(action="unidad.creada").exists()


# ---------- integrantes ----------
def test_el_encargado_agrega_servidores_pero_no_encargados(mundo, monkeypatch):
    avisos = []
    monkeypatch.setattr(push, "notificar", lambda **kw: avisos.append(kw) or 0)
    nueva = cuenta("55 0000 0050", "Nueva Cuenta", "miembro")
    url = f"/api/unidades/{mundo['cafeteria'].pk}/integrantes/"
    api = api_de(mundo["encargada"])
    ok = api.post(url, {"whatsapp": nueva.whatsapp, "rol": "servidor"}, format="json")
    assert ok.status_code == 201
    assert any(a["titulo"] == "Te agregaron a una unidad" for a in avisos)
    for rol in ("encargado", "respaldo"):
        r = api.post(url, {"whatsapp": nueva.whatsapp, "rol": rol}, format="json")
        assert r.status_code == 403
    assert (
        api_de(mundo["pastor"])
        .post(url, {"whatsapp": nueva.whatsapp, "rol": "respaldo"}, format="json")
        .status_code
        == 201
    )


def test_un_servidor_no_gestiona_integrantes(mundo):
    url = f"/api/unidades/{mundo['cafeteria'].pk}/integrantes/"
    r = api_de(mundo["servidor"]).post(
        url, {"whatsapp": "55 9000 0001", "nombre": "X", "acepta_datos": True}, format="json"
    )
    assert r.status_code == 403


def test_alta_de_una_persona_nueva_exige_consentimiento(mundo):
    url = f"/api/unidades/{mundo['cafeteria'].pk}/integrantes/"
    api = api_de(mundo["encargada"])
    datos = {"whatsapp": "55 9000 0002", "nombre": "Vecino Nuevo", "rol": "servidor"}
    assert api.post(url, datos, format="json").status_code == 400
    assert api.post(url, {**datos, "acepta_datos": True}, format="json").status_code == 201


def test_cambiar_rol_quitar_y_deshacer(mundo):
    caf = mundo["cafeteria"]
    servidor_m = UnidadMiembro.objects.get(unidad=caf, persona=mundo["servidor"].persona)
    url = f"/api/unidades/{caf.pk}/integrantes/{servidor_m.pk}/"
    encargada = api_de(mundo["encargada"])
    assert encargada.patch(url, {"rol": "respaldo"}, format="json").status_code == 403
    assert (
        api_de(mundo["pastor"]).patch(url, {"rol": "respaldo"}, format="json").json()["rol"]
        == "respaldo"
    )
    # el encargado tampoco quita a un respaldo; sí a un servidor
    assert encargada.delete(url).status_code == 403
    servidor_m.rol = "servidor"
    servidor_m.save()
    assert encargada.delete(url).status_code == 204
    assert encargada.post(f"{url}restaurar/", {}, format="json").status_code == 200
    assert UnidadMiembro.objects.get(pk=servidor_m.pk).activo


# ---------- tablero de la unidad ----------
def test_el_tablero_de_la_unidad_lo_publica_el_encargado_y_lo_leen_los_integrantes(mundo):
    base = {
        "origen_tipo": "unidad",
        "origen_id": mundo["cafeteria"].pk,
        "texto": "Mañana hay junta",
    }
    assert api_de(mundo["servidor"]).post("/api/tablero/", base, format="json").status_code == 403
    assert api_de(mundo["respaldo"]).post("/api/tablero/", base, format="json").status_code == 201
    lectura = api_de(mundo["servidor"]).get(
        f"/api/tablero/?origen_tipo=unidad&origen_id={mundo['cafeteria'].pk}"
    )
    assert lectura.status_code == 200
    assert api_de(mundo["lider"]).get(
        f"/api/tablero/?origen_tipo=unidad&origen_id={mundo['cafeteria'].pk}"
    ).status_code in (403, 404)


# ---------- avisos masivos ----------
def test_destinos_segun_lo_que_cada_quien_puede_publicar(mundo):
    destinos = lambda u: {  # noqa: E731
        (d["tipo"], d["id"]) for d in api_de(u).get("/api/tablero/destinos/").json()
    }
    pastor = destinos(mundo["pastor"])
    assert ("iglesia", 1) in pastor
    assert ("grupo", mundo["norte"].pk) in pastor
    assert ("unidad", mundo["cafeteria"].pk) in pastor and (
        "unidad",
        mundo["libreria"].pk,
    ) in pastor
    assert destinos(mundo["encargada"]) == {("unidad", mundo["cafeteria"].pk)}
    assert destinos(mundo["lider"]) == {("grupo", mundo["norte"].pk)}
    assert destinos(mundo["ajena"]) == set()


def test_el_pastor_envia_un_aviso_a_la_iglesia_grupos_y_unidades(mundo):
    r = api_de(mundo["pastor"]).post(
        "/api/tablero/masivo/",
        {
            "texto": "Domingo de ayuno",
            "destinos": [
                {"tipo": "iglesia", "id": 1},
                {"tipo": "grupo", "id": mundo["norte"].pk},
                {"tipo": "unidad", "id": mundo["cafeteria"].pk},
                {"tipo": "unidad", "id": mundo["cafeteria"].pk},  # repetido: se envía una vez
            ],
        },
        format="json",
    )
    assert r.status_code == 201
    assert len(r.json()["enviados"]) == 3 and r.json()["omitidos"] == []
    assert Mensaje.objects.filter(texto="Domingo de ayuno").count() == 3
    assert AuditEvent.objects.filter(action="tablero.masivo").exists()
    # toda la iglesia lo lee, aun quien no pertenece a nada
    assert (
        api_de(mundo["ajena"]).get("/api/tablero/?origen_tipo=iglesia&origen_id=1").status_code
        == 200
    )


def test_cada_destino_respeta_sus_propios_permisos(mundo):
    r = api_de(mundo["encargada"]).post(
        "/api/tablero/masivo/",
        {
            "texto": "Aviso de la cafetería",
            "destinos": [
                {"tipo": "unidad", "id": mundo["cafeteria"].pk},
                {"tipo": "unidad", "id": mundo["libreria"].pk},  # ahí solo es servidora
                {"tipo": "iglesia", "id": 1},
            ],
        },
        format="json",
    )
    assert r.status_code == 201
    assert [e["tipo"] for e in r.json()["enviados"]] == ["unidad"]
    assert {(o["tipo"], o["id"]) for o in r.json()["omitidos"]} == {
        ("unidad", mundo["libreria"].pk),
        ("iglesia", 1),
    }


def test_avisos_a_personas_solo_los_lee_la_persona(mundo):
    destino = mundo["ajena"].persona.pk
    r = api_de(mundo["secretaria"]).post(
        "/api/tablero/masivo/",
        {"texto": "Pasa a la oficina", "destinos": [{"tipo": "persona", "id": destino}]},
        format="json",
    )
    assert len(r.json()["enviados"]) == 1
    propios = api_de(mundo["ajena"]).get("/api/tablero/mis-tableros/").json()
    assert any(t["tipo"] == "persona" and t["etiqueta"] == "Avisos para ti" for t in propios)
    assert api_de(mundo["lider"]).get(
        f"/api/tablero/?origen_tipo=persona&origen_id={destino}"
    ).status_code in (
        403,
        404,
    )
    # quien no tiene el permiso no escribe a personas
    sin = api_de(mundo["encargada"]).post(
        "/api/tablero/masivo/",
        {"texto": "Hola", "destinos": [{"tipo": "persona", "id": destino}]},
        format="json",
    )
    assert sin.json()["enviados"] == []


def test_validaciones_del_envio_masivo(mundo):
    api = api_de(mundo["pastor"])
    assert (
        api.post("/api/tablero/masivo/", {"texto": "x", "destinos": []}, format="json").status_code
        == 400
    )
    sin_texto = api.post(
        "/api/tablero/masivo/",
        {"texto": "  ", "destinos": [{"tipo": "iglesia", "id": 1}]},
        format="json",
    )
    assert sin_texto.status_code == 400
    muchos = [{"tipo": "unidad", "id": i} for i in range(1, 70)]
    assert (
        api.post(
            "/api/tablero/masivo/", {"texto": "x", "destinos": muchos}, format="json"
        ).status_code
        == 400
    )


def test_el_aviso_general_notifica_a_todos_menos_a_quien_lo_envia(mundo, monkeypatch):
    avisos = []
    monkeypatch.setattr(push, "notificar", lambda **kw: avisos.append(kw) or 0)
    api_de(mundo["pastor"]).post(
        "/api/tablero/masivo/",
        {"texto": "Culto especial", "destinos": [{"tipo": "iglesia", "id": 1}]},
        format="json",
    )
    assert avisos and avisos[0]["excluir"] == mundo["pastor"]
    assert avisos[0]["puede_recibir"](mundo["ajena"]) is True


# ---------- permisos nuevos en los roles ----------
def test_los_permisos_nuevos_llegan_a_los_roles_que_corresponden(db):
    permisos = lambda clave: set(Rol.objects.get(clave=clave).permisos)  # noqa: E731
    for clave in ("pastor", "secretaria"):
        assert {
            "unidades.gestionar",
            "unidades.ver_todas",
            "avisos.iglesia",
            "avisos.personas",
        } <= permisos(clave)
    assert "unidades.ver_todas" in permisos("anciano")
    assert not permisos("anciano") & {"unidades.gestionar", "avisos.iglesia", "avisos.personas"}
    assert not permisos("admin_tecnico") & {
        "unidades.ver_todas",
        "avisos.iglesia",
        "avisos.personas",
    }
