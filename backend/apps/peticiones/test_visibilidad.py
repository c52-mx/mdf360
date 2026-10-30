"""Alcance de lectura de las peticiones: solo líderes, mi grupo o equipo de oración."""

import pytest

from apps.grupos.models import GrupoMiembro

from .models import Peticion
from .test_peticiones import _limpiar, api_de, api_de_vigente, crear, cuenta, m  # noqa: F401


def con_alcance(m, visibilidad, quien="lider", ocultar=False, datos=None):
    return crear(m, quien, visibilidad=visibilidad, ocultar_nombre=ocultar, datos=datos)


def ve(m, quien):
    return len(api_de(m[quien]).get("/api/peticiones/").json()["results"])


@pytest.fixture
def rico(m):
    """Agrega un asistente de cada grupo (con cuenta) y a un miembro del equipo de oración."""
    m["asistente"] = cuenta("55 0000 0020", "Asistente Norte", "miembro")
    GrupoMiembro.objects.create(grupo=m["norte"], persona=m["asistente"].persona, rol="asistente")
    m["asistente_sur"] = cuenta("55 0000 0021", "Asistente Sur", "miembro")
    GrupoMiembro.objects.create(grupo=m["sur"], persona=m["asistente_sur"].persona, rol="asistente")
    m["oracion"] = cuenta("55 0000 0022", "Intercesor", "equipo_oracion")
    return m


def test_por_defecto_solo_lideres(rico):
    assert crear(rico).status_code == 201
    assert Peticion.objects.get().visibilidad == "lideres"
    for quien in ("lider", "sup", "pastor", "anciano"):
        assert ve(rico, quien) == 1, quien
    for quien in ("asistente", "secre", "tesorero", "oracion", "asistente_sur", "admin"):
        assert ve(rico, quien) == 0, quien


def test_un_integrante_no_ve_las_peticiones_del_grupo_aunque_sean_de_alcance_grupo(rico):
    """Cada persona ve solo las suyas; el líder o rol superior ve las de su grupo."""
    assert con_alcance(rico, "grupo").status_code == 201
    for quien in ("lider", "sup", "pastor", "anciano"):
        assert ve(rico, quien) == 1, quien
    for quien in (
        "asistente",
        "secre",
        "tesorero",
        "asistente_sur",
        "lider_sur",
        "oracion",
        "admin",
    ):
        assert ve(rico, quien) == 0, quien


def test_el_asistente_ve_su_peticion_personal_y_no_las_de_otros(rico):
    crear(rico, "lider", visibilidad="equipo")
    propia = api_de(rico["asistente"]).post(
        "/api/peticiones/",
        {
            "origen_tipo": "persona",
            "origen_id": rico["asistente"].pk,
            "datos": {"peticion": "Por mi familia", "solicitante": "Yo"},
        },
        format="json",
    )
    assert propia.status_code == 201
    vistas = api_de(rico["asistente"]).get("/api/peticiones/").json()["results"]
    assert [v["datos"]["peticion"] for v in vistas] == ["Por mi familia"]


def test_alcance_equipo_lo_leen_los_lideres_y_el_equipo_de_oracion(rico):
    assert con_alcance(rico, "equipo").status_code == 201
    for quien in ("lider", "oracion", "pastor"):
        assert ve(rico, quien) == 1, quien
    for quien in ("asistente", "secre", "asistente_sur", "lider_sur", "admin"):
        assert ve(rico, quien) == 0, quien
    assert Peticion.objects.get().visibilidad == "equipo"


def test_el_equipo_no_ve_las_de_alcance_grupo_ni_solo_lideres(rico):
    con_alcance(rico, "grupo")
    con_alcance(rico, "lideres")
    assert ve(rico, "oracion") == 0
    # y las del equipo, de cualquier origen, sí
    GrupoMiembro.objects.create(grupo=rico["sur"], persona=rico["pastor"].persona, rol="asistente")
    crear(rico, "pastor", "sur", visibilidad="equipo")
    solo = api_de(rico["oracion"]).get("/api/peticiones/").json()["results"]
    assert (
        len(solo) == 1 and "Conexión Sur" in solo[0]["origen"]["etiqueta"]
    )  # origen siempre visible


def test_quien_no_es_lider_no_gestiona_aunque_la_vea(rico):
    con_alcance(rico, "equipo")
    pid = Peticion.objects.get().pk
    r = api_de(rico["oracion"]).patch(
        f"/api/peticiones/{pid}/", {"estado": "atendida"}, format="json"
    )
    assert r.status_code == 403
    for quien in ("asistente", "secre"):  # un integrante ni siquiera la ve
        r = api_de(rico[quien]).patch(
            f"/api/peticiones/{pid}/", {"estado": "atendida"}, format="json"
        )
        assert r.status_code == 404, quien
    ok = api_de(rico["lider"]).patch(
        f"/api/peticiones/{pid}/", {"estado": "atendida"}, format="json"
    )
    assert ok.status_code == 200
    # quien no la ve ni siquiera sabe que existe
    ajeno = api_de(rico["asistente_sur"]).patch(
        f"/api/peticiones/{pid}/", {"estado": "atendida"}, format="json"
    )
    assert ajeno.status_code == 404
    assert (
        api_de(rico["lider"]).get("/api/peticiones/").json()["results"][0]["puede_gestionar"]
        is True
    )
    otra = api_de(rico["oracion"]).get("/api/peticiones/").json()["results"][0]
    assert otra["puede_gestionar"] is False


def test_ocultar_nombre_solo_lo_ven_lideres_y_quien_la_registro(rico):
    datos = {"peticion": "Por mi matrimonio", "solicitante": "Carmen Ruiz"}
    con_alcance(rico, "equipo", ocultar=True, datos=datos)
    d = api_de(rico["oracion"]).get("/api/peticiones/").json()["results"][0]["datos"]
    assert d["peticion"] == "Por mi matrimonio" and "solicitante" not in d
    for quien in ("lider", "sup", "pastor", "anciano"):
        d = api_de(rico[quien]).get("/api/peticiones/").json()["results"][0]["datos"]
        assert d["solicitante"] == "Carmen Ruiz", quien
    # sin ocultar, el equipo de oración ve el nombre
    Peticion.objects.all().delete()
    con_alcance(rico, "equipo", ocultar=False, datos=datos)
    visto = api_de(rico["oracion"]).get("/api/peticiones/").json()["results"][0]["datos"]
    assert visto["solicitante"] == "Carmen Ruiz"


def test_ocultar_nombre_no_aplica_si_es_solo_lideres(rico):
    con_alcance(rico, "lideres", ocultar=True)
    assert Peticion.objects.get().ocultar_nombre is False


def test_la_secretaria_que_la_registra_si_ve_el_nombre(rico):
    r = crear(rico, "secre", visibilidad="grupo", ocultar_nombre=True)
    assert r.status_code == 201
    assert r.json()["datos"]["solicitante"] == "María"  # es quien la registró


def test_alcance_invalido(rico):
    assert crear(rico, visibilidad="todos").status_code == 400


def test_el_alcance_por_defecto_es_configurable(rico):
    api = api_de(rico["pastor"])
    url = "/api/config/peticiones.visibilidad_por_defecto/"
    assert api.patch(url, {"valor": "grupo"}, format="json").status_code == 200
    assert api.patch(url, {"valor": "todos"}, format="json").status_code == 400
    crear(rico)  # sin indicar alcance
    assert Peticion.objects.get().visibilidad == "grupo"
    formulario = api_de(rico["asistente"]).get("/api/peticiones/formulario/").json()
    assert formulario["visibilidad_por_defecto"] == "grupo"
    cfg = {c["clave"]: c for c in api.get("/api/config/").json()}
    assert cfg["peticiones.visibilidad_por_defecto"]["opciones"] == ["lideres", "grupo", "equipo"]


def test_el_campo_que_identifica_se_define_en_el_formulario(rico):
    f = api_de(rico["lider"]).get("/api/peticiones/formulario/").json()["campos"]
    esperado = {"peticion": False, "solicitante": True, "categoria": False}
    assert {c["clave"]: c["identifica"] for c in f} == esperado
    campos = api_de_vigente()
    campos.append(
        {"clave": "telefono", "etiqueta": "Teléfono", "tipo": "texto", "identifica": True}
    )
    api_de(rico["pastor"]).put("/api/peticiones/formulario/", {"campos": campos}, format="json")
    con_alcance(rico, "equipo", ocultar=True, datos={"peticion": "x", "telefono": "5511112222"})
    d = api_de(rico["oracion"]).get("/api/peticiones/").json()["results"][0]["datos"]
    assert "telefono" not in d


def test_el_rol_equipo_de_oracion_se_asigna_desde_roles(rico):
    persona = cuenta("55 0000 0030", "Nuevo intercesor")
    r = api_de(rico["pastor"]).post(
        f"/api/auth/users/{persona.pk}/roles/", {"roles": ["equipo_oracion"]}, format="json"
    )
    assert r.status_code == 200 and "peticiones.equipo_oracion" in r.json()["permisos"]
    con_alcance(rico, "equipo")
    assert len(api_de(persona).get("/api/peticiones/").json()["results"]) == 1
    # el rol no abre nada más: ni personas ni bitácora
    assert api_de(persona).get("/api/personas/").status_code == 403
    assert api_de(persona).get("/api/auditoria/").status_code == 403


def test_el_formulario_informa_los_dias_de_conservacion_para_la_leyenda(rico):
    api = api_de(rico["lider"])
    assert api.get("/api/peticiones/formulario/").json()["dias_retencion"] == 30
    api_de(rico["pastor"]).patch(
        "/api/config/peticiones.dias_retencion/", {"valor": 15}, format="json"
    )
    assert api.get("/api/peticiones/formulario/").json()["dias_retencion"] == 15


# ---------- quién registra y quién lee depende del rol que se configure ----------
def test_registrar_peticiones_del_grupo_es_un_permiso_del_rol(rico):
    from apps.accounts.models import RolEquipo

    assert crear(rico, "secre").status_code == 201
    rol = RolEquipo.objects.get(ambito="grupo", clave="secretario")
    rol.permisos = sorted(set(rol.permisos) - {"peticiones_registrar"})
    rol.save()
    assert crear(rico, "secre").status_code == 403
    anf = RolEquipo.objects.get(ambito="grupo", clave="tesorero")
    anf.permisos = sorted({*anf.permisos, "peticiones_registrar"})
    anf.save()
    assert crear(rico, "tesorero").status_code == 201


def test_ver_las_de_solo_lideres_es_un_permiso_del_rol(rico):
    from apps.accounts.models import RolEquipo

    con_alcance(rico, "lideres")
    assert ve(rico, "sup") == 1 and ve(rico, "tesorero") == 0
    sup = RolEquipo.objects.get(ambito="grupo", clave="supervisor")
    sup.permisos = sorted(set(sup.permisos) - {"peticiones_ver"})
    sup.save()
    assert ve(rico, "sup") == 0
    tes = RolEquipo.objects.get(ambito="grupo", clave="tesorero")
    tes.permisos = sorted({*tes.permisos, "peticiones_ver"})
    tes.save()
    assert ve(rico, "tesorero") == 1
