"""Roles de ministerio y de grupo configurables, y peticiones de oración por ministerio."""

from apps.accounts.models import RolEquipo
from apps.core.models import AuditEvent

from .models import UnidadMiembro
from .test_unidades import _limpiar, api_de, cuenta, mundo  # noqa: F401

DATOS_PETICION = {"peticion": "Por la cafetería", "solicitante": "María", "categoria": "Salud"}


def crear_rol(user, nombre, permisos, ambito="ministerio"):
    return api_de(user).post(
        "/api/auth/roles-equipo/",
        {"ambito": ambito, "nombre": nombre, "permisos": permisos},
        format="json",
    )


# ---------- configuración de roles ----------
def test_los_tres_roles_base_de_ministerio_vienen_configurados(db):
    base = {r.clave: r for r in RolEquipo.objects.filter(ambito="ministerio")}
    assert set(base) == {"encargado", "respaldo", "servidor"}
    assert all(r.es_base for r in base.values())
    assert "integrantes" in base["encargado"].permisos
    assert "integrantes" in base["respaldo"].permisos
    assert base["servidor"].permisos == ["ver"]


def test_los_roles_base_de_grupo_replican_lo_que_ya_se_hacia(db):
    permisos = {r.clave: set(r.permisos) for r in RolEquipo.objects.filter(ambito="grupo")}
    claves = {"lider", "respaldo", "supervisor", "secretario", "anfitrion", "tesorero"}
    assert set(permisos) == claves | {"servidor", "asistente"}
    assert permisos["lider"] >= {"ver", "integrantes", "historial", "capturar", "corregir"}
    assert permisos["supervisor"] == {
        "ver", "historial", "estudio", "avisos", "ofrendas_ver", "peticiones_ver",
    }  # fmt: skip
    assert permisos["secretario"] == {
        "ver", "capturar", "estudio", "avisos", "ofrendas_capturar", "peticiones_registrar",
    }  # fmt: skip
    assert permisos["tesorero"] == {"ofrendas_ver", "ofrendas_avalar"}
    assert permisos["asistente"] == permisos["anfitrion"] == set()


def test_un_rol_nuevo_de_ministerio_se_crea_y_se_asigna(mundo):  # noqa: F811
    nuevo = crear_rol(mundo["pastor"], "Coordinador de turno", ["ver", "avisos"])
    assert nuevo.status_code == 201
    clave = nuevo.json()["clave"]
    caf = mundo["cafeteria"]
    miembro = UnidadMiembro.objects.get(unidad=caf, persona=mundo["servidor"].persona)
    # el encargado puede dárselo a un servidor (no administra personas) y este ya publica avisos
    ok = api_de(mundo["encargada"]).patch(
        f"/api/unidades/{caf.pk}/integrantes/{miembro.pk}/", {"rol": clave}, format="json"
    )
    assert ok.status_code == 200 and ok.json()["rol_display"] == "Coordinador de turno"
    aviso = api_de(mundo["servidor"]).post(
        "/api/tablero/",
        {"origen_tipo": "unidad", "origen_id": caf.pk, "texto": "Hoy hay pan"},
        format="json",
    )
    assert aviso.status_code == 201


def test_quitar_un_permiso_al_rol_cambia_lo_que_puede_hacer(mundo):  # noqa: F811
    cambio = api_de(mundo["pastor"]).patch(
        "/api/auth/roles-equipo/ministerio/encargado/",
        {"permisos": ["ver", "avisos"]},
        format="json",
    )
    assert cambio.status_code == 200
    caf = api_de(mundo["encargada"]).get(f"/api/unidades/{mundo['cafeteria'].pk}/").json()
    assert caf["puede_gestionar"] is False  # ya no administra integrantes


def test_un_rol_de_gestion_solo_lo_asigna_la_administracion_aunque_sea_nuevo(mundo):  # noqa: F811
    clave = crear_rol(mundo["pastor"], "Coordinador", ["ver", "integrantes"]).json()["clave"]
    url = f"/api/unidades/{mundo['cafeteria'].pk}/integrantes/"
    datos = {"whatsapp": mundo["ajena"].whatsapp, "rol": clave}
    assert api_de(mundo["encargada"]).post(url, datos, format="json").status_code == 403
    assert api_de(mundo["pastor"]).post(url, datos, format="json").status_code == 201


def test_solo_quien_administra_roles_los_configura(mundo):  # noqa: F811
    for quien in ("encargada", "anciano", "lider"):
        assert crear_rol(mundo[quien], "Otro", ["ver"]).status_code == 403
    assert crear_rol(mundo["secretaria"], "Otro", ["ver"]).status_code == 201
    assert AuditEvent.objects.filter(action="rbac.rol_equipo_creado").exists()


def test_reglas_de_los_roles_de_equipo(mundo):  # noqa: F811
    pastor = api_de(mundo["pastor"])
    url = "/api/auth/roles-equipo/ministerio/servidor/"
    assert pastor.patch(url, {"activo": False}, format="json").status_code == 400  # es base
    assert pastor.patch(url, {"permisos": ["inventado"]}, format="json").status_code == 400
    assert pastor.patch(url, {"nombre": "Encargado"}, format="json").status_code == 400  # repetido
    assert (
        pastor.patch("/api/auth/roles-equipo/ministerio/nada/", {}, format="json").status_code
        == 404
    )
    # un permiso de grupo no sirve en un ministerio
    en_grupo = pastor.patch(
        "/api/auth/roles-equipo/ministerio/servidor/",
        {"permisos": ["ofrendas_avalar"]},
        format="json",
    )
    assert en_grupo.status_code == 400
    # un rol en uso no se desactiva; uno sin uso, sí
    creado = crear_rol(mundo["pastor"], "Temporal", ["ver"]).json()["clave"]
    UnidadMiembro.objects.create(
        unidad=mundo["libreria"], persona=mundo["ajena"].persona, rol=creado
    )
    ruta = f"/api/auth/roles-equipo/ministerio/{creado}/"
    assert pastor.patch(ruta, {"activo": False}, format="json").status_code == 400
    UnidadMiembro.objects.filter(rol=creado).delete()
    assert pastor.patch(ruta, {"activo": False}, format="json").json()["activo"] is False
    # y un rol desactivado ya no se puede asignar
    r = api_de(mundo["encargada"]).post(
        f"/api/unidades/{mundo['cafeteria'].pk}/integrantes/",
        {"whatsapp": mundo["ajena"].whatsapp, "rol": creado},
        format="json",
    )
    assert r.status_code == 400


# ---------- peticiones de oración por ministerio ----------
def peticion(user, unidad, **extra):
    cuerpo = {"origen_tipo": "unidad", "origen_id": unidad.pk, "datos": DATOS_PETICION, **extra}
    return api_de(user).post("/api/peticiones/", cuerpo, format="json")


def vistas(user):
    return len(api_de(user).get("/api/peticiones/").json()["results"])


def test_las_peticiones_de_un_ministerio_las_registra_y_ve_quien_su_rol_permite(mundo):  # noqa: F811
    r = peticion(mundo["encargada"], mundo["cafeteria"])
    assert r.status_code == 201
    assert r.json()["origen"]["etiqueta"] == "Ministerio · Cafetería"
    assert peticion(mundo["servidor"], mundo["cafeteria"]).status_code == 403  # su rol no registra
    assert (
        peticion(mundo["lider"], mundo["cafeteria"]).status_code == 403
    )  # liderar un grupo no sirve
    assert vistas(mundo["encargada"]) == vistas(mundo["respaldo"]) == 1
    assert vistas(mundo["servidor"]) == 0  # por defecto solo las ven quienes lideran
    assert vistas(mundo["lider"]) == 0 and vistas(mundo["ajena"]) == 0
    assert vistas(mundo["pastor"]) == vistas(mundo["anciano"]) == 1


def test_una_peticion_compartida_con_todo_el_ministerio_la_ve_quien_sirve_en_el(mundo):  # noqa: F811
    assert peticion(mundo["encargada"], mundo["cafeteria"], visibilidad="grupo").status_code == 201
    assert vistas(mundo["servidor"]) == 1
    otro = cuenta("55 0000 0040", "Otro Servidor", "servidor")
    UnidadMiembro.objects.create(unidad=mundo["libreria"], persona=otro.persona, rol="servidor")
    assert vistas(otro) == 0  # servir en otro ministerio no abre este
