"""«Deshacer» de las acciones que quitan algo: mensajes del tablero e integrantes del grupo."""

from apps.core.models import AuditEvent
from apps.grupos.models import GrupoMiembro

from .models import Mensaje
from .test_tablero import _limpiar, api_de, leer, m, publicar  # noqa: F401


def test_se_restaura_un_mensaje_borrado(m):
    a = publicar(m).json()["id"]
    api_de(m["lider"]).delete(f"/api/tablero/{a}/")
    assert leer(m, "asistente").json() == []
    r = api_de(m["lider"]).post(f"/api/tablero/{a}/restaurar/")
    assert r.status_code == 200 and r.json()["texto"]
    assert len(leer(m, "asistente").json()) == 1
    assert Mensaje.objects.get(pk=a).eliminado is False
    assert AuditEvent.objects.filter(action="tablero.restaurado").exists()


def test_solo_quien_modera_restaura(m):
    a = publicar(m).json()["id"]
    api_de(m["lider"]).delete(f"/api/tablero/{a}/")
    assert api_de(m["asistente"]).post(f"/api/tablero/{a}/restaurar/").status_code == 403
    assert api_de(m["otro"]).post(f"/api/tablero/{a}/restaurar/").status_code == 404
    assert api_de(m["sup"]).post(f"/api/tablero/{a}/restaurar/").status_code == 200


def test_no_se_restaura_lo_que_no_esta_borrado(m):
    a = publicar(m).json()["id"]
    assert api_de(m["lider"]).post(f"/api/tablero/{a}/restaurar/").status_code == 404


def test_se_restaura_un_integrante_quitado(m):
    miembro = GrupoMiembro.objects.get(persona=m["asistente"].persona)
    url = f"/api/grupos/{m['norte'].pk}/integrantes/{miembro.pk}/"
    assert api_de(m["lider"]).delete(url).status_code == 204
    miembro.refresh_from_db()
    assert miembro.activo is False
    r = api_de(m["lider"]).post(url + "restaurar/")
    assert r.status_code == 200 and r.json()["rol"] == "asistente"
    miembro.refresh_from_db()
    assert miembro.activo is True
    assert AuditEvent.objects.filter(action="grupo.integrante_restaurado").exists()


def test_restaurar_integrante_respeta_los_permisos(m):
    miembro = GrupoMiembro.objects.get(persona=m["asistente"].persona)
    url = f"/api/grupos/{m['norte'].pk}/integrantes/{miembro.pk}/"
    api_de(m["lider"]).delete(url)
    assert api_de(m["secre"]).post(url + "restaurar/").status_code == 403
    assert api_de(m["otro"]).post(url + "restaurar/").status_code == 404
    # un Líder no restaura a otro Líder: solo la administración
    lider_m = GrupoMiembro.objects.get(persona=m["lider"].persona, rol="lider")
    api_de(m["pastor"]).delete(f"/api/grupos/{m['norte'].pk}/integrantes/{lider_m.pk}/")
    assert (
        api_de(m["sup"])
        .post(f"/api/grupos/{m['norte'].pk}/integrantes/{lider_m.pk}/restaurar/")
        .status_code
        == 403
    )  # el supervisor consulta pero no gestiona integrantes
    assert (
        api_de(m["pastor"])
        .post(f"/api/grupos/{m['norte'].pk}/integrantes/{lider_m.pk}/restaurar/")
        .status_code
        == 200
    )
