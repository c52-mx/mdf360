"""Organización de grupos (paso 3): sector y casa, filtros, suspensión, cambio de rol y reuniones por día."""

from apps.core.models import AuditEvent

from .models import Asistencia, GrupoMiembro, Reunion
from .test_grupos import api_de, cuenta, mundo  # noqa: F401  (fixture)


# ---------- sector y casa ----------
def test_el_sector_es_una_letra_y_la_casa_un_numero(mundo):
    api = api_de(mundo["pastor"])
    r = api.patch(f"/api/grupos/{mundo['norte'].pk}/", {"sector": "k", "casa": 6}, format="json")
    assert r.status_code == 200
    assert r.json()["sector"] == "K"
    mundo["norte"].refresh_from_db()
    assert mundo["norte"].ubicacion.endswith("Casa 6")
    malo = api.patch(f"/api/grupos/{mundo['norte'].pk}/", {"sector": "Norte"}, format="json")
    assert malo.status_code == 400
    assert (
        api.patch(f"/api/grupos/{mundo['norte'].pk}/", {"casa": 0}, format="json").status_code
        == 400
    )


def test_la_ubicacion_se_arma_con_lo_capturado(mundo):
    norte = mundo["norte"]
    norte.sector, norte.casa = "K", 6
    norte.save()
    r = api_de(mundo["pastor"]).get(f"/api/grupos/{norte.pk}/").json()
    assert r["ubicacion"] == "Sector K, Casa 6"


# ---------- filtros ----------
def test_filtros_por_dia_sector_lider_y_texto(mundo):
    norte, sur = mundo["norte"], mundo["sur"]
    norte.sector = "K"
    norte.save()
    api = api_de(mundo["pastor"])
    nombres = lambda qs: sorted(g["nombre"] for g in api.get(f"/api/grupos/?{qs}").json())  # noqa: E731
    assert nombres("dia=3") == ["Conexión Norte"]
    assert nombres("sector=k") == ["Conexión Norte"]
    assert nombres("lider=laura") == ["Conexión Norte"]
    assert nombres("lider=otro") == ["Conexión Sur"]
    assert nombres("q=sur") == ["Conexión Sur"]
    assert nombres("") == ["Conexión Norte", "Conexión Sur"]
    assert sur.pk


# ---------- suspensión ----------
def test_suspender_y_reactivar_un_grupo(mundo):
    norte = mundo["norte"]
    url = f"/api/grupos/{norte.pk}"
    # solo la administración
    lider = api_de(mundo["lider"])
    assert lider.post(f"{url}/suspender/", {"motivo": "x"}, format="json").status_code == 403
    api = api_de(mundo["pastor"])
    assert api.post(f"{url}/suspender/", {"motivo": "  "}, format="json").status_code == 400
    r = api.post(f"{url}/suspender/", {"motivo": "El anfitrión se mudó"}, format="json")
    assert r.status_code == 200 and r.json()["suspendido"] is True
    assert r.json()["suspension_motivo"] == "El anfitrión se mudó"
    assert AuditEvent.objects.filter(action="grupo.suspendido").exists()

    # no se abren reuniones mientras esté suspendido
    abrir = api_de(mundo["lider"]).post(f"{url}/reuniones/", {}, format="json")
    assert abrir.status_code == 400 and abrir.json()["code"] == "suspended"

    # filtros por estado
    estado = lambda e: [g["nombre"] for g in api.get(f"/api/grupos/?estado={e}").json()]  # noqa: E731
    assert estado("suspendidos") == ["Conexión Norte"]
    assert "Conexión Norte" not in estado("activos")

    # el dashboard no lo cuenta ni lo avisa, pero lo informa
    tablero = api.get("/api/grupos/dashboard/").json()
    assert [g["nombre"] for g in tablero["grupos"]] == ["Conexión Sur"]
    assert tablero["resumen"]["suspendidos"] == 1
    assert tablero["suspendidos"][0]["motivo"] == "El anfitrión se mudó"

    assert api.post(f"{url}/reactivar/", {}, format="json").json()["suspendido"] is False
    assert AuditEvent.objects.filter(action="grupo.reactivado").exists()
    assert api_de(mundo["lider"]).post(f"{url}/reuniones/", {}, format="json").status_code == 201


# ---------- cambio de rol ----------
def test_el_lider_cambia_el_rol_de_un_integrante_pero_no_a_lider(mundo):
    norte = mundo["norte"]
    nuevo = cuenta("55 0000 0050", "Nuevo Asistente", "miembro")
    m = GrupoMiembro.objects.create(grupo=norte, persona=nuevo.persona, rol="asistente")
    url = f"/api/grupos/{norte.pk}/integrantes/{m.pk}/"
    api = api_de(mundo["lider"])
    r = api.patch(url, {"rol": "anfitrion"}, format="json")
    assert r.status_code == 200 and r.json()["rol"] == "anfitrion"
    assert AuditEvent.objects.filter(action="grupo.integrante_rol").exists()
    assert api.patch(url, {"rol": "lider"}, format="json").status_code == 403
    assert api_de(mundo["pastor"]).patch(url, {"rol": "lider"}, format="json").status_code == 200
    # un líder tampoco toca a otro líder
    lider_m = GrupoMiembro.objects.get(grupo=norte, persona=mundo["lider"].persona)
    r = api.patch(
        f"/api/grupos/{norte.pk}/integrantes/{lider_m.pk}/", {"rol": "asistente"}, format="json"
    )
    assert r.status_code == 403


def test_un_secretario_no_cambia_roles(mundo):
    norte = mundo["norte"]
    m = GrupoMiembro.objects.get(grupo=norte, rol="supervisor")
    r = api_de(mundo["secre"]).patch(
        f"/api/grupos/{norte.pk}/integrantes/{m.pk}/", {"rol": "asistente"}, format="json"
    )
    assert r.status_code == 403


# ---------- reuniones por día ----------
def test_cada_reunion_trae_lo_que_ocurrio_ese_dia(mundo):
    norte = mundo["norte"]
    reunion = Reunion.objects.create(grupo=norte, notas="Se oró por la familia Pérez")
    for u, presente in ((mundo["lider"], True), (mundo["secre"], False)):
        Asistencia.objects.create(reunion=reunion, persona=u.persona, presente=presente)

    fila = api_de(mundo["lider"]).get(f"/api/grupos/{norte.pk}/").json()["reuniones"][0]
    assert fila["presentes"] == 1 and fila["registrados"] == 2
    assert fila["notas"] == "Se oró por la familia Pérez"
    assert fila["ofrendas"] == {"cantidad": 0, "total": "0"}  # el líder ve finanzas de su grupo
    # el anciano consulta el grupo pero no ve finanzas
    sup = api_de(mundo["anciano"]).get(f"/api/grupos/{norte.pk}/").json()["reuniones"][0]
    assert sup["ofrendas"] is None
