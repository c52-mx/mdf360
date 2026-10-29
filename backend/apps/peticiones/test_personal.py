"""Cualquier persona con sesión puede pedir oración; cada quien ve las suyas."""

from .test_peticiones import _limpiar, api_de, cuenta  # noqa: F401

DATOS = {"peticion": "Por mi familia", "solicitante": "Yo", "categoria": "Familia"}


def pedir(user, origen_id=None, **extra):
    cuerpo = {"origen_tipo": "persona", "origen_id": origen_id or user.pk, "datos": DATOS, **extra}
    return api_de(user).post("/api/peticiones/", cuerpo, format="json")


def vistas(user):
    return len(api_de(user).get("/api/peticiones/").json()["results"])


def test_todos_piden_oracion_y_cada_quien_ve_las_suyas(db):
    miembro = cuenta("55 0000 0301", "Mónica Miembro", "miembro")
    otra = cuenta("55 0000 0302", "Olga Otra", "miembro")
    pastor = cuenta("55 0000 0303", "Pastor", "pastor")
    r = pedir(miembro)
    assert r.status_code == 201 and r.json()["origen"]["etiqueta"] == "Petición personal"
    assert vistas(miembro) == 1  # la ve quien la pidió
    assert vistas(otra) == 0  # nadie más
    assert vistas(pastor) == 1  # la dirección ve todas
    assert pedir(otra, origen_id=miembro.pk).status_code == 403  # no pide a nombre de otra cuenta


def test_con_alcance_equipo_la_lee_el_equipo_de_oracion(db):
    miembro = cuenta("55 0000 0311", "Mónica Miembro", "miembro")
    intercesor = cuenta("55 0000 0312", "Intercesor", "equipo_oracion")
    assert pedir(miembro).status_code == 201
    assert vistas(intercesor) == 0  # por defecto solo líderes
    assert pedir(miembro, visibilidad="equipo").status_code == 201
    assert vistas(intercesor) == 1
