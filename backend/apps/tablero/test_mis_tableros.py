"""Pantalla «Avisos»: los tableros que cada persona puede leer, con no leídos y permiso de publicar."""

from apps.grupos.models import GrupoMiembro

from .test_tablero import _limpiar, api_de, cuenta, m, publicar  # noqa: F401


def tableros(m, quien, tipo="grupo"):
    """Los tableros de un tipo. Todos tienen además «Toda la iglesia»."""
    todos = api_de(m[quien]).get("/api/tablero/mis-tableros/").json()
    return [t for t in todos if t["tipo"] == tipo]


def test_cada_quien_lista_solo_sus_tableros(m):
    assert [t["etiqueta"] for t in tableros(m, "asistente")] == [
        "Grupo de Conexión · Conexión Norte"
    ]
    assert [t["etiqueta"] for t in tableros(m, "otro")] == ["Grupo de Conexión · Conexión Sur"]
    assert len(tableros(m, "pastor")) == len(tableros(m, "anciano")) == 2  # ven todos los grupos
    sin_grupo = cuenta("55 0000 0090", "Sin grupo", "miembro")
    generales = api_de(sin_grupo).get("/api/tablero/mis-tableros/").json()
    assert [t["tipo"] for t in generales] == ["iglesia"]  # sin grupos ni unidades


def test_indica_no_leidos_y_si_puede_publicar(m):
    publicar(m, texto="Uno")
    publicar(m, texto="Dos")
    fila = tableros(m, "asistente")[0]
    assert fila["no_leidos"] == 2 and fila["puede_publicar"] is False
    assert fila["tipo"] == "grupo" and fila["id"] == m["norte"].pk
    propia = tableros(m, "lider")[0]
    assert propia["no_leidos"] == 0 and propia["puede_publicar"] is True  # sus mensajes no cuentan


def test_un_integrante_dado_de_baja_deja_de_ver_el_tablero(m):
    GrupoMiembro.objects.filter(persona=m["asistente"].persona).update(activo=False)
    assert tableros(m, "asistente") == []
    assert (
        api_de(m["asistente"])
        .get(f"/api/tablero/?origen_tipo=grupo&origen_id={m['norte'].pk}")
        .status_code
        == 404
    )


def test_requiere_sesion(db):
    from rest_framework.test import APIClient

    assert APIClient().get("/api/tablero/mis-tableros/").status_code == 403
