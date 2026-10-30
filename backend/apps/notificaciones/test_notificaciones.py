import json

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from pywebpush import WebPushException

from apps.core import config
from apps.core.models import AuditEvent
from apps.grupos import services as grupos_services
from apps.tablero import services as tablero
from apps.tablero.test_tablero import api_de, cuenta, m  # noqa: F401

from . import push
from .models import Suscripcion


class _Respuesta:
    def __init__(self, status_code):
        self.status_code = status_code


@pytest.fixture(autouse=True)
def _push(settings, monkeypatch):
    settings.VAPID_PUBLIC_KEY = "publica"
    settings.VAPID_PRIVATE_KEY = "privada"
    settings.PUSH_EN_SEGUNDO_PLANO = False
    enviados = []
    monkeypatch.setattr(push, "_transporte", lambda info, payload: enviados.append((info, payload)))
    return enviados


@pytest.fixture
def enviados(_push):
    return _push


def suscribir(user, n=1):
    return Suscripcion.objects.create(
        usuario=user, endpoint=f"https://push.example/{user.pk}/{n}", p256dh="p", auth="a"
    )


def _destinos(enviados):
    return sorted(info["endpoint"] for info, _ in enviados)


def test_suscribir_y_cancelar(m):  # noqa: F811
    api = api_de(m["lider"])
    cuerpo = {"endpoint": "https://push.example/abc", "keys": {"p256dh": "k1", "auth": "k2"}}
    r = api.post("/api/notificaciones/suscribir/", cuerpo, format="json")
    assert r.status_code == 201
    assert AuditEvent.objects.filter(action="notificaciones.suscrita").count() == 1
    # repetir no duplica
    assert api.post("/api/notificaciones/suscribir/", cuerpo, format="json").status_code == 200
    assert Suscripcion.objects.count() == 1
    r = api.post(
        "/api/notificaciones/desuscribir/", {"endpoint": cuerpo["endpoint"]}, format="json"
    )
    assert r.status_code == 204
    assert Suscripcion.objects.count() == 0


def test_un_dispositivo_pasa_al_ultimo_usuario_que_lo_activa(m):  # noqa: F811
    cuerpo = {"endpoint": "https://push.example/compartido", "keys": {"p256dh": "k1", "auth": "k2"}}
    api_de(m["lider"]).post("/api/notificaciones/suscribir/", cuerpo, format="json")
    api_de(m["asistente"]).post("/api/notificaciones/suscribir/", cuerpo, format="json")
    assert Suscripcion.objects.get().usuario == m["asistente"]


def test_nadie_cancela_el_dispositivo_de_otro(m):  # noqa: F811
    s = suscribir(m["lider"])
    api_de(m["asistente"]).post(
        "/api/notificaciones/desuscribir/", {"endpoint": s.endpoint}, format="json"
    )
    assert Suscripcion.objects.filter(pk=s.pk).exists()


def test_config_expone_la_clave_publica_solo_si_esta_activo(m, settings):  # noqa: F811
    api = api_de(m["lider"])
    assert api.get("/api/notificaciones/config/").json() == {
        "disponible": True,
        "clave_publica": "publica",
    }
    settings.VAPID_PRIVATE_KEY = ""
    assert api.get("/api/notificaciones/config/").json() == {
        "disponible": False,
        "clave_publica": "",
    }
    assert (
        api.post(
            "/api/notificaciones/suscribir/",
            {"endpoint": "https://push.example/x", "keys": {"p256dh": "a", "auth": "b"}},
            format="json",
        ).status_code
        == 409
    )


def test_se_puede_apagar_desde_configuracion(m, enviados):  # noqa: F811
    from apps.core.models import Configuracion

    suscribir(m["asistente"])
    Configuracion.objects.update_or_create(
        clave="notificaciones.activas", defaults={"valor": False}
    )
    assert config.obtener("notificaciones.activas") is False
    tablero.publicar(origen_tipo="grupo", origen_id=m["norte"].pk, texto="Hola", actor=m["lider"])
    assert enviados == []


@pytest.mark.django_db
def test_un_mensaje_avisa_solo_a_quien_puede_leerlo(
    m, enviados, django_capture_on_commit_callbacks
):  # noqa: F811
    s_asistente = suscribir(m["asistente"])
    s_lider = suscribir(m["lider"])  # el autor no se avisa a sí mismo
    suscribir(m["otro"])  # integrante de otro grupo
    with django_capture_on_commit_callbacks(execute=True):
        tablero.publicar(
            origen_tipo="grupo", origen_id=m["norte"].pk, texto="Mañana a las 7", actor=m["lider"]
        )
    assert _destinos(enviados) == [s_asistente.endpoint]
    assert s_lider.endpoint not in _destinos(enviados)
    datos = json.loads(enviados[0][1])
    assert datos["titulo"] == "Grupo de Conexión · Conexión Norte"
    assert datos["cuerpo"] == "Laura Líder: Mañana a las 7"
    assert datos["url"] == f"/grupos/{m['norte'].pk}"


@pytest.mark.django_db
def test_el_cuerpo_largo_se_recorta(m, enviados, django_capture_on_commit_callbacks):  # noqa: F811
    suscribir(m["asistente"])
    with django_capture_on_commit_callbacks(execute=True):
        tablero.publicar(
            origen_tipo="grupo", origen_id=m["norte"].pk, texto="palabra " * 100, actor=m["lider"]
        )
    assert len(json.loads(enviados[0][1])["cuerpo"]) <= push.CUERPO_MAX


@pytest.mark.django_db
def test_un_estudio_nuevo_avisa_a_lideres_y_asistentes_pero_no_a_quien_no_lo_ve(  # noqa: F811
    m, enviados, django_capture_on_commit_callbacks
):
    s_lider = suscribir(m["lider"])
    s_asistente = suscribir(m["asistente"])
    pdf = SimpleUploadedFile("estudio.pdf", b"%PDF-1.4 prueba", content_type="application/pdf")
    with django_capture_on_commit_callbacks(execute=True):
        grupos_services.guardar_estudio(
            semana=__import__("datetime").date(2026, 10, 26),
            titulo="Fundamentos de la vida cristiana",
            archivos={"pdf_adultos": pdf},
            actor=m["pastor"],
        )
    assert sorted(_destinos(enviados)) == sorted([s_lider.endpoint, s_asistente.endpoint])
    datos = json.loads(enviados[0][1])
    assert datos["titulo"] == "Estudio de la semana"
    assert datos["url"] == "/estudios"


@pytest.mark.django_db
def test_un_dispositivo_caducado_se_elimina(m, monkeypatch, django_capture_on_commit_callbacks):  # noqa: F811
    s = suscribir(m["asistente"])

    def falla(info, payload):
        raise WebPushException("Gone", response=_Respuesta(410))

    monkeypatch.setattr(push, "_transporte", falla)
    with django_capture_on_commit_callbacks(execute=True):
        tablero.publicar(
            origen_tipo="grupo", origen_id=m["norte"].pk, texto="Hola", actor=m["lider"]
        )
    assert not Suscripcion.objects.filter(pk=s.pk).exists()


@pytest.mark.django_db
def test_un_error_pasajero_conserva_el_dispositivo_y_no_rompe_la_publicacion(  # noqa: F811
    m, monkeypatch, django_capture_on_commit_callbacks
):
    s = suscribir(m["asistente"])

    def falla(info, payload):
        raise WebPushException("Servidor caído", response=_Respuesta(503))

    monkeypatch.setattr(push, "_transporte", falla)
    with django_capture_on_commit_callbacks(execute=True):
        tablero.publicar(
            origen_tipo="grupo", origen_id=m["norte"].pk, texto="Hola", actor=m["lider"]
        )
    assert Suscripcion.objects.filter(pk=s.pk).exists()


def test_prueba_envia_solo_a_mis_dispositivos(m, enviados, django_capture_on_commit_callbacks):  # noqa: F811
    mio = suscribir(m["lider"])
    suscribir(m["asistente"])
    api = api_de(m["lider"])
    with django_capture_on_commit_callbacks(execute=True):
        r = api.post("/api/notificaciones/probar/")
    assert r.status_code == 200 and r.json() == {"dispositivos": 1}
    assert _destinos(enviados) == [mio.endpoint]


def test_prueba_sin_dispositivos_avisa(m):  # noqa: F811
    assert api_de(m["lider"]).post("/api/notificaciones/probar/").status_code == 409


def test_exige_sesion(db):
    from rest_framework.test import APIClient

    assert APIClient().get("/api/notificaciones/config/").status_code in (401, 403)
