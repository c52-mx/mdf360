import itertools
from datetime import date, timedelta

import pytest
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import AsignacionRol, Rol, User
from apps.personas import services as personas
from apps.peticiones import services as peticiones

from .models import Asistencia, Grupo, GrupoMiembro, Ofrenda, Reunion

PIN = "482915"
FUERTE = "Tesoro-2026-x"


@pytest.fixture(autouse=True)
def _limpiar():
    cache.clear()


def cuenta(whatsapp, nombre, *roles, credencial=PIN):
    user = User.objects.create_user(whatsapp, nombre=nombre)
    user.set_password(credencial)
    user.save()
    for clave in roles:
        AsignacionRol.objects.create(usuario=user, rol=Rol.objects.get(clave=clave))
    personas.ensure_persona_for_user(user)
    return user


def api_de(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


def dashboard(user):
    return api_de(user).get("/api/grupos/dashboard/").json()


def lunes_pasado(semanas=1):
    hoy = timezone.localdate()
    return hoy - timedelta(days=hoy.weekday()) - timedelta(weeks=semanas - 1)


_numeros = itertools.count(1)


def con_lista(grupo, fecha, presentes, ausentes):
    reunion = Reunion.objects.create(grupo=grupo, fecha=fecha)
    for i in range(presentes + ausentes):
        n = next(_numeros)
        p = personas.crear_persona(
            datos={"nombre": f"Persona {n}", "whatsapp": f"56{n:08d}"}, acepta_datos=True
        )
        Asistencia.objects.create(reunion=reunion, persona=p, presente=i < presentes)
    return reunion


@pytest.fixture
def m(db):
    norte = Grupo.objects.create(nombre="Conexión Norte", dia_semana=0)  # lunes: ya "toca" siempre
    sur = Grupo.objects.create(nombre="Conexión Sur", dia_semana=0)
    g = dict(
        pastor=cuenta("55 0000 0001", "Pastor", "pastor", credencial=FUERTE),
        anciano=cuenta("55 0000 0002", "Anciano", "anciano"),
        lider=cuenta("55 0000 0003", "Líder Norte", "lider"),
        secre=cuenta("55 0000 0004", "Secretaria", "secretario"),
        sup=cuenta("55 0000 0005", "Supervisor", "supervisor"),
        tesorero=cuenta("55 0000 0006", "Tesorero", "tesorero", credencial=FUERTE),
        lider_sur=cuenta("55 0000 0007", "Líder Sur", "lider"),
    )
    for clave, grupo, rol in (
        ("lider", norte, "lider"), ("secre", norte, "secretario"), ("sup", norte, "supervisor"),
        ("sup", sur, "supervisor"), ("tesorero", norte, "tesorero"), ("lider_sur", sur, "lider"),
    ):  # fmt: skip
        GrupoMiembro.objects.create(grupo=grupo, persona=g[clave].persona, rol=rol)
    return {**g, "norte": norte, "sur": sur}


# ---------- alcance ----------
def test_cada_quien_ve_solo_sus_grupos(m):
    nombres = lambda u: sorted(g["nombre"] for g in dashboard(u)["grupos"])  # noqa: E731
    assert nombres(m["lider"]) == ["Conexión Norte"]
    assert nombres(m["lider_sur"]) == ["Conexión Sur"]
    assert nombres(m["sup"]) == ["Conexión Norte", "Conexión Sur"]
    assert nombres(m["pastor"]) == nombres(m["anciano"]) == ["Conexión Norte", "Conexión Sur"]


def test_el_secretario_y_el_tesorero_no_tienen_dashboard(m):
    assert dashboard(m["secre"])["grupos"] == []  # no consulta el historial
    assert dashboard(m["tesorero"])["grupos"] == []
    assert APIClient().get("/api/grupos/dashboard/").status_code == 403


# ---------- métricas ----------
def test_asistencia_y_serie_semanal(m):
    con_lista(m["norte"], lunes_pasado(1), presentes=3, ausentes=1)  # esta semana: 75 %
    con_lista(m["norte"], lunes_pasado(2), presentes=1, ausentes=1)  # semana anterior: 50 %
    d = dashboard(m["lider"])
    g = d["grupos"][0]
    assert g["integrantes"] == 4 and g["reuniones_8_semanas"] == 2
    assert g["asistencia_pct"] == round(100 * 4 / 6)
    assert [u["presentes"] for u in g["ultimas"]] == [1, 3]  # de la más vieja a la más nueva
    assert len(d["serie"]) == 8 and d["serie"][-1]["pct"] == 75 and d["serie"][-2]["pct"] == 50
    assert d["resumen"]["grupos"] == 1 and d["resumen"]["asistencia_pct"] == round(100 * 4 / 6)


def test_los_grupos_sin_datos_no_rompen_el_reporte(m):
    d = dashboard(m["pastor"])
    assert all(g["asistencia_pct"] is None and g["ultimas"] == [] for g in d["grupos"])
    assert d["resumen"]["asistencia_pct"] is None


def test_alerta_si_no_hay_lista_esta_semana_y_ya_toco(m):
    d = dashboard(m["sup"])
    tipos = {(a["tipo"], a["grupo"]) for a in d["alertas"]}
    assert ("sin_lista", "Conexión Norte") in tipos and ("sin_lista", "Conexión Sur") in tipos
    con_lista(m["norte"], lunes_pasado(1), presentes=2, ausentes=0)
    tipos = {(a["tipo"], a["grupo"]) for a in dashboard(m["sup"])["alertas"]}
    assert ("sin_lista", "Conexión Norte") not in tipos and ("sin_lista", "Conexión Sur") in tipos


def test_un_grupo_sin_dia_definido_no_genera_alerta_de_lista(m):
    Grupo.objects.filter(pk=m["norte"].pk).update(dia_semana=None)
    tipos = {(a["tipo"], a["grupo"]) for a in dashboard(m["lider"])["alertas"]}
    assert ("sin_lista", "Conexión Norte") not in tipos


def test_alerta_de_asistencia_baja_con_umbral_configurable(m):
    con_lista(m["norte"], lunes_pasado(1), presentes=1, ausentes=3)  # 25 %
    tipos = [a["tipo"] for a in dashboard(m["lider"])["alertas"]]
    assert "asistencia_baja" in tipos
    api_de(m["pastor"]).patch(
        "/api/config/grupos.asistencia_minima_pct/", {"valor": 20}, format="json"
    )
    assert "asistencia_baja" not in [a["tipo"] for a in dashboard(m["lider"])["alertas"]]
    assert dashboard(m["lider"])["resumen"]["asistencia_minima_pct"] == 20
    r = api_de(m["pastor"]).patch(
        "/api/config/grupos.asistencia_minima_pct/", {"valor": 150}, format="json"
    )
    assert r.status_code == 400


# ---------- confidencialidad ----------
def _ofrenda(m, grupo="norte", estado="avalada", monto="500"):
    reunion = Reunion.objects.filter(grupo=m[grupo]).first() or Reunion.objects.create(
        grupo=m[grupo], fecha=timezone.localdate()
    )
    return Ofrenda.objects.create(
        reunion=reunion, tipo="especial", concepto=f"{estado}{Ofrenda.objects.count()}",
        monto=monto, estado=estado,
    )  # fmt: skip


def test_las_ofrendas_solo_se_ven_si_se_puede_ver_finanzas(m):
    _ofrenda(m, estado="avalada", monto="500")
    _ofrenda(m, estado="diferencia", monto="100")
    _ofrenda(m, estado="pendiente", monto="50")
    for quien in ("lider", "sup", "pastor"):
        of = dashboard(m[quien])["grupos"][0]["ofrendas"]
        assert of == {"avalado_30_dias": "500.00", "pendientes": 1, "con_diferencia": 1}, quien
    assert dashboard(m["anciano"])["grupos"][0]["ofrendas"] is None  # el Anciano no ve finanzas
    assert "ofrenda_con_diferencia" in [a["tipo"] for a in dashboard(m["lider"])["alertas"]]
    assert "ofrenda_con_diferencia" not in [a["tipo"] for a in dashboard(m["anciano"])["alertas"]]


def test_las_peticiones_activas_respetan_el_alcance(m):
    peticiones.registrar_peticion(
        origen_tipo="grupo", origen_id=m["norte"].pk, datos={"peticion": "Por la salud"},
        actor=m["lider"], visibilidad="lideres",
    )  # fmt: skip

    def cuenta_de(u):
        norte = next(g for g in dashboard(u)["grupos"] if g["nombre"] == "Conexión Norte")
        return norte["peticiones_activas"]

    assert cuenta_de(m["lider"]) == cuenta_de(m["sup"]) == cuenta_de(m["pastor"]) == 1
    sur = next(g for g in dashboard(m["lider"])["grupos"])
    assert sur["peticiones_activas"] == 1
    assert (
        next(g for g in dashboard(m["sup"])["grupos"] if g["nombre"] == "Conexión Sur")[
            "peticiones_activas"
        ]
        == 0
    )


def test_el_dashboard_no_incluye_datos_de_personas(m):
    con_lista(m["norte"], lunes_pasado(1), presentes=2, ausentes=1)
    texto = str(dashboard(m["pastor"]))
    assert "Persona " not in texto and "whatsapp" not in texto.lower()


_ = date
