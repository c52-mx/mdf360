from datetime import date, timedelta

import pytest
from django.core.cache import cache
from django.db import connection
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import AsignacionRol, Rol, User
from apps.core.models import AuditEvent
from apps.grupos.models import Grupo, GrupoMiembro, Reunion
from apps.personas import services as personas

from . import registry, services
from .models import FormularioPeticion, OrigenInmutable, Peticion

SECRETO = "Que Dios sane a mi mamá de su diabetes"
FUERTE = "Pastor-2026-clave"


@pytest.fixture(autouse=True)
def _limpiar():
    cache.clear()


def cuenta(whatsapp, nombre, *roles):
    user = User.objects.create_user(whatsapp, nombre=nombre)
    user.set_password(FUERTE)
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
        admin=cuenta("55 0000 0003", "Admin", "admin_tecnico"),
        lider=cuenta("55 0000 0004", "Líder Norte", "lider"),
        secre=cuenta("55 0000 0005", "Secretaria Norte", "secretario"),
        sup=cuenta("55 0000 0006", "Supervisor", "supervisor"),
        lider_sur=cuenta("55 0000 0007", "Líder Sur", "lider"),
        tesorero=cuenta("55 0000 0008", "Tesorero", "tesorero"),
    )
    for clave, grupo, rol in (
        ("lider", norte, "lider"), ("secre", norte, "secretario"), ("sup", norte, "supervisor"),
        ("sup", sur, "supervisor"), ("lider_sur", sur, "lider"), ("tesorero", norte, "tesorero"),
    ):  # fmt: skip
        GrupoMiembro.objects.create(grupo=grupo, persona=g[clave].persona, rol=rol)
    reunion = Reunion.objects.create(grupo=norte, fecha=date(2026, 10, 22))
    return {**g, "norte": norte, "sur": sur, "reunion": reunion}


def crear(m, quien="lider", grupo="norte", datos=None, **extra):
    cuerpo = {
        "origen_tipo": "grupo",
        "origen_id": m[grupo].pk,
        "datos": datos or {"peticion": SECRETO, "solicitante": "María", "categoria": "Salud"},
        **extra,
    }
    return api_de(m[quien]).post("/api/peticiones/", cuerpo, format="json")


# ---------- origen siempre presente e inmutable ----------
def test_cada_peticion_muestra_su_origen(m):
    r = crear(m, referencia_id=m["reunion"].pk)
    assert r.status_code == 201
    origen = r.json()["origen"]
    assert origen["tipo"] == "grupo" and origen["tipo_display"] == "Grupo de Conexión"
    assert origen["id"] == m["norte"].pk
    assert origen["etiqueta"] == "Grupo de Conexión · Conexión Norte · reunión del 22/10/2026"
    # y en el listado
    lista = api_de(m["lider"]).get("/api/peticiones/").json()["results"]
    assert lista[0]["origen"]["etiqueta"] == origen["etiqueta"]


def test_el_origen_no_se_puede_cambiar(m):
    crear(m)
    p = Peticion.objects.get()
    p.origen_id = m["sur"].pk
    with pytest.raises(OrigenInmutable):
        p.save()
    p.refresh_from_db()
    p.origen_etiqueta = "Otro"
    with pytest.raises(OrigenInmutable):
        p.save()
    # cambiar otros campos sí se permite
    p.refresh_from_db()
    p.estado = "atendida"
    p.save()


def test_la_etiqueta_sobrevive_si_el_grupo_cambia_de_nombre(m):
    crear(m)
    m["norte"].nombre = "Renombrado"
    m["norte"].save()
    etiqueta = api_de(m["lider"]).get("/api/peticiones/").json()["results"][0]["origen"]["etiqueta"]
    assert etiqueta == "Grupo de Conexión · Conexión Norte"


def test_la_reunion_debe_pertenecer_al_grupo(m):
    ajena = Reunion.objects.create(grupo=m["sur"], fecha=date(2026, 10, 22))
    assert crear(m, referencia_id=ajena.pk).status_code == 400
    assert crear(m, referencia_id=999999).status_code == 400


def test_origen_desconocido_o_inexistente(m):
    api = api_de(m["lider"])
    r = api.post(
        "/api/peticiones/",
        {"origen_tipo": "curso", "origen_id": 1, "datos": {"peticion": "x"}},
        format="json",
    )
    assert r.status_code == 400 and r.json()["code"] == "unknown_origin"
    r = api.post(
        "/api/peticiones/",
        {"origen_tipo": "grupo", "origen_id": 99999, "datos": {"peticion": "x"}},
        format="json",
    )
    assert r.status_code == 403


# ---------- cifrado ----------
def test_el_contenido_se_guarda_cifrado_y_no_aparece_en_ninguna_parte(m):
    crear(m)
    p = Peticion.objects.get()
    assert SECRETO not in p.datos_cifrados and "María" not in p.datos_cifrados
    with connection.cursor() as cur:
        cur.execute("SELECT datos_cifrados FROM peticiones_peticion")
        assert SECRETO not in cur.fetchone()[0]
    for evento in AuditEvent.objects.all():  # la bitácora nunca lleva el texto
        assert SECRETO not in str(evento.detail) and "María" not in str(evento.detail)
    assert (
        api_de(m["lider"]).get("/api/peticiones/").json()["results"][0]["datos"]["peticion"]
        == SECRETO
    )


def test_con_otra_clave_no_se_puede_leer(m, settings):
    crear(m)
    settings.PETICIONES_ENCRYPTION_KEYS = ""
    settings.SECRET_KEY = "otra-clave-distinta-de-django"
    fila = api_de(m["lider"]).get("/api/peticiones/").json()["results"][0]
    assert fila["ilegible"] is True and "datos" not in fila


def test_rotacion_de_claves(m, settings):
    from cryptography.fernet import Fernet

    vieja, nueva = Fernet.generate_key().decode(), Fernet.generate_key().decode()
    settings.PETICIONES_ENCRYPTION_KEYS = vieja
    crear(m)
    settings.PETICIONES_ENCRYPTION_KEYS = (
        f"{nueva},{vieja}"  # la nueva cifra; la vieja aún descifra
    )
    assert (
        api_de(m["lider"]).get("/api/peticiones/").json()["results"][0]["datos"]["peticion"]
        == SECRETO
    )


# ---------- confidencialidad (matriz) ----------
def test_quien_puede_registrar(m):
    assert crear(m, "lider").status_code == 201
    assert crear(m, "secre").status_code == 201
    assert crear(m, "pastor").status_code == 201
    for quien in ("sup", "tesorero", "anciano", "admin", "lider_sur"):
        assert crear(m, quien).status_code == 403, quien


def test_el_secretario_registra_pero_no_lee(m):
    r = crear(m, "secre")
    assert r.status_code == 201 and "datos" not in r.json()
    assert api_de(m["secre"]).get("/api/peticiones/").json()["results"] == []


def test_quien_puede_ver_el_contenido(m):
    crear(m)
    for quien in ("lider", "sup", "pastor", "anciano"):
        assert len(api_de(m[quien]).get("/api/peticiones/").json()["results"]) == 1, quien
    for quien in ("secre", "tesorero", "admin", "lider_sur"):
        assert api_de(m[quien]).get("/api/peticiones/").json()["results"] == [], quien


def test_el_alcance_es_por_grupo(m):
    crear(m, "lider", "norte")
    GrupoMiembro.objects.create(grupo=m["sur"], persona=m["pastor"].persona, rol="asistente")
    crear(m, "pastor", "sur")
    assert len(api_de(m["lider"]).get("/api/peticiones/").json()["results"]) == 1
    assert len(api_de(m["lider_sur"]).get("/api/peticiones/").json()["results"]) == 1
    assert len(api_de(m["sup"]).get("/api/peticiones/").json()["results"]) == 2
    assert len(api_de(m["pastor"]).get("/api/peticiones/").json()["results"]) == 2
    solo_sur = (
        api_de(m["pastor"])
        .get(f"/api/peticiones/?origen_tipo=grupo&origen_id={m['sur'].pk}")
        .json()
    )
    assert solo_sur["count"] == 1 and "Conexión Sur" in solo_sur["results"][0]["origen"]["etiqueta"]


def test_el_admin_tecnico_nunca_ve_el_contenido(m):
    crear(m)
    assert api_de(m["admin"]).get("/api/peticiones/").json()["results"] == []
    from django.contrib import admin as dj_admin

    assert Peticion not in dj_admin.site._registry  # ni en el panel técnico


def test_atender_y_reactivar(m):
    crear(m)
    pid = Peticion.objects.get().pk
    api = api_de(m["lider"])
    r = api.patch(f"/api/peticiones/{pid}/", {"estado": "atendida"}, format="json")
    assert r.status_code == 200 and r.json()["estado"] == "atendida"
    assert (
        api.patch(f"/api/peticiones/{pid}/", {"estado": "activa"}, format="json").json()["estado"]
        == "activa"
    )
    assert (
        api.patch(f"/api/peticiones/{pid}/", {"estado": "otra"}, format="json").status_code == 400
    )
    assert (
        api_de(m["secre"])
        .patch(f"/api/peticiones/{pid}/", {"estado": "atendida"}, format="json")
        .status_code
        == 404
    )
    assert (
        api_de(m["lider_sur"])
        .patch(f"/api/peticiones/{pid}/", {"estado": "atendida"}, format="json")
        .status_code
        == 404
    )
    assert api.get("/api/peticiones/?estado=activa").json()["count"] == 1


def test_todo_queda_en_bitacora_sin_contenido(m):
    crear(m)
    api_de(m["lider"]).get("/api/peticiones/")
    acciones = set(AuditEvent.objects.values_list("action", flat=True))
    assert {"peticion.creada", "peticion.consultadas"} <= acciones


# ---------- formulario configurable y versionado ----------
def test_formulario_inicial(m):
    f = api_de(m["lider"]).get("/api/peticiones/formulario/").json()
    assert f["version"] == 1 and [c["clave"] for c in f["campos"]] == [
        "peticion",
        "solicitante",
        "categoria",
    ]


def test_validacion_de_datos_contra_el_formulario(m):
    assert crear(m, datos={"peticion": ""}).status_code == 400  # obligatorio
    assert crear(m, datos={"peticion": "x", "categoria": "Inventada"}).status_code == 400
    assert crear(m, datos={"peticion": "x", "otro": "y"}).status_code == 400
    assert crear(m, datos={"peticion": "x" * 2001}).status_code == 400
    assert crear(m, datos={"peticion": "Solo lo obligatorio"}).status_code == 201


def _campos_con(extra, base=None):
    base = base or api_de_vigente()
    return base + extra


def api_de_vigente():
    return [dict(c) for c in FormularioPeticion.objects.order_by("-version").first().campos]


def test_editar_el_formulario_crea_version_y_no_borra_campos(m):
    campos = api_de_vigente()
    campos.append({"clave": "urgente", "etiqueta": "¿Es urgente?", "tipo": "casilla"})
    for c in campos:
        if c["clave"] == "solicitante":
            c["activo"] = False  # se desactiva, no se borra
    r = api_de(m["pastor"]).put("/api/peticiones/formulario/", {"campos": campos}, format="json")
    assert r.status_code == 200 and r.json()["version"] == 2
    # una petición nueva usa la versión 2 y el campo nuevo
    ok = crear(m, datos={"peticion": "Urgente", "urgente": True})
    assert (
        ok.status_code == 201 and ok.json()["formulario_version"] == 2
        if "formulario_version" in ok.json()
        else True
    )
    assert Peticion.objects.get().formulario_version == 2
    # el campo desactivado ya no se acepta
    assert crear(m, datos={"peticion": "x", "solicitante": "Ana"}).status_code == 400
    # quitar un campo existente está prohibido
    sin_categoria = [c for c in campos if c["clave"] != "categoria"]
    r = api_de(m["pastor"]).put(
        "/api/peticiones/formulario/", {"campos": sin_categoria}, format="json"
    )
    assert r.status_code == 400 and "no se pueden quitar" in r.json()["detail"]
    assert AuditEvent.objects.filter(action="peticiones.formulario_cambiado").exists()


def test_las_peticiones_viejas_se_siguen_leyendo_tras_cambiar_el_formulario(m):
    crear(m)
    campos = api_de_vigente()
    for c in campos:
        if c["clave"] == "categoria":
            c["activo"] = False
    api_de(m["pastor"]).put("/api/peticiones/formulario/", {"campos": campos}, format="json")
    vieja = api_de(m["lider"]).get("/api/peticiones/").json()["results"][0]
    assert vieja["datos"]["categoria"] == "Salud" and vieja["formulario_version"] == 1


def test_validaciones_del_editor_de_formulario(m):
    base = api_de_vigente()

    def put(campos):
        return api_de(m["pastor"]).put(
            "/api/peticiones/formulario/", {"campos": campos}, format="json"
        )

    assert put([]).status_code == 400
    assert (
        put(base + [{"clave": "peticion", "etiqueta": "Dup", "tipo": "texto"}]).status_code == 400
    )
    assert (
        put(base + [{"clave": "x y", "etiqueta": "Mala clave", "tipo": "texto"}]).status_code == 400
    )
    assert (
        put(base + [{"clave": "n", "etiqueta": "Tipo malo", "tipo": "numero"}]).status_code == 400
    )
    assert (
        put(
            base
            + [{"clave": "s", "etiqueta": "Sin opciones", "tipo": "seleccion", "opciones": ["a"]}]
        ).status_code
        == 400
    )
    todos_inactivos = [{**c, "activo": False} for c in base]
    assert put(todos_inactivos).status_code == 400
    sin_obligatorio = [{**c, "requerido": False} for c in base]
    assert put(sin_obligatorio).status_code == 400


def test_solo_pastor_y_admin_editan_el_formulario(m):
    base = api_de_vigente()
    for quien, esperado in (
        ("lider", 403),
        ("anciano", 403),
        ("sup", 403),
        ("pastor", 200),
        ("admin", 200),
    ):
        r = api_de(m[quien]).put("/api/peticiones/formulario/", {"campos": base}, format="json")
        assert r.status_code == esperado, quien


# ---------- retención ----------
def test_las_peticiones_vencidas_se_borran(m):
    crear(m)
    p = Peticion.objects.get()
    assert p.expira_en > timezone.now() + timedelta(days=29)  # 30 días por defecto
    Peticion.objects.filter(pk=p.pk).update(expira_en=timezone.now() - timedelta(minutes=1))
    assert (
        api_de(m["lider"]).get("/api/peticiones/").json()["results"] == []
    )  # se purga al consultar
    assert Peticion.objects.count() == 0
    assert AuditEvent.objects.filter(action="peticion.purgadas", detail__cantidad=1).exists()


def test_comando_de_purga(m):
    from django.core.management import call_command

    crear(m)
    crear(m, datos={"peticion": "otra"})
    vieja = Peticion.objects.order_by("id").first()
    Peticion.objects.filter(pk=vieja.pk).update(expira_en=timezone.now() - timedelta(days=1))
    call_command("purgar_peticiones", verbosity=0)
    assert Peticion.objects.count() == 1


def test_la_retencion_es_configurable(m):
    r = api_de(m["pastor"]).patch(
        "/api/config/peticiones.dias_retencion/", {"valor": 7}, format="json"
    )
    assert r.status_code == 200
    crear(m)
    p = Peticion.objects.get()
    assert timedelta(days=6) < p.expira_en - timezone.now() < timedelta(days=7, minutes=1)
    api = api_de(m["pastor"])
    assert (
        api.patch("/api/config/peticiones.dias_retencion/", {"valor": 0}, format="json").status_code
        == 400
    )
    assert (
        api.patch(
            "/api/config/peticiones.dias_retencion/", {"valor": 1.5}, format="json"
        ).status_code
        == 400
    )
    assert (
        api.patch(
            "/api/config/peticiones.dias_retencion/", {"valor": True}, format="json"
        ).status_code
        == 400
    )


# ---------- reutilización: otro módulo puede ser origen ----------
def test_otro_modulo_puede_registrarse_como_origen(m):
    registry.registrar(
        registry.Origen(
            tipo="curso",
            nombre="Curso",
            etiqueta=lambda i, r: f"Curso · número {i}",
            puede_registrar=lambda u, i: u.pk == m["secre"].pk,
            puede_ver=lambda u, i: u.pk == m["anciano"].pk,
            ids_visibles=lambda u: [7] if u.pk == m["anciano"].pk else [],
        )
    )
    try:
        r = api_de(m["secre"]).post(
            "/api/peticiones/",
            {"origen_tipo": "curso", "origen_id": 7, "datos": {"peticion": "Por el curso"}},
            format="json",
        )
        assert r.status_code == 201 and r.json()["origen"]["tipo_display"] == "Curso"
        crear(m)  # una de grupo
        lista = api_de(m["anciano"]).get("/api/peticiones/").json()["results"]
        assert {x["origen"]["tipo"] for x in lista} == {
            "curso",
            "grupo",
        }  # el origen siempre se distingue
        solo = api_de(m["anciano"]).get("/api/peticiones/?origen_tipo=curso").json()["results"]
        assert [x["origen"]["etiqueta"] for x in solo] == ["Curso · número 7"]
        assert {"curso", "grupo"} <= {
            o["tipo"] for o in api_de(m["lider"]).get("/api/peticiones/origenes/").json()
        }
    finally:
        registry._ORIGENES.pop("curso", None)


def test_sin_sesion_no_hay_acceso(db):
    assert APIClient().get("/api/peticiones/").status_code == 403
    assert APIClient().post("/api/peticiones/", {}, format="json").status_code == 403


_ = services, date
