"""«Mi cuenta»: cada persona corrige sus datos básicos, sin tocar acceso ni relaciones."""

import io

import pytest
from PIL import Image
from rest_framework.test import APIClient

from apps.accounts.models import AsignacionRol, Rol, User
from apps.core.models import AuditEvent
from apps.grupos.models import Grupo, GrupoMiembro

from . import services
from .models import Consentimiento

PIN = "482915"
URL = "/api/personas/mi-perfil/"


@pytest.fixture
def yo(db):
    user = User.objects.create_user("55 0000 0100", pin=PIN, nombre="Ana Lopes")
    AsignacionRol.objects.create(usuario=user, rol=Rol.objects.get(clave="miembro"))
    persona = services.ensure_persona_for_user(user)
    grupo = Grupo.objects.create(nombre="Norte")
    GrupoMiembro.objects.create(grupo=grupo, persona=persona, rol="asistente")
    return user


def api_de(user):
    cliente = APIClient()
    cliente.force_authenticate(user)
    return cliente


def png():
    buffer = io.BytesIO()
    Image.new("RGB", (40, 40), "red").save(buffer, format="PNG")
    buffer.seek(0)
    buffer.name = "yo.png"
    return buffer


def test_la_persona_corrige_su_nombre_y_sus_datos_basicos(yo):
    r = api_de(yo).patch(
        URL,
        {
            "nombre": "Ana",
            "apellido_paterno": "López",
            "colonia": "Roma",
            "oracion_familias": True,
            "fecha_nacimiento": "1990-05-04",
        },
        format="json",
    )
    assert r.status_code == 200 and r.json()["nombre_completo"] == "Ana López"
    yo.refresh_from_db()
    assert yo.nombre == "Ana López"  # el nombre que se ve en la aplicación también se corrige
    assert api_de(yo).get(URL).json()["colonia"] == "Roma"
    evento = AuditEvent.objects.filter(action="persona.perfil_editado").latest("pk")
    assert "nombre" in evento.detail["campos"]
    assert "Roma" not in str(evento.detail)  # la bitácora no guarda los valores


def test_no_puede_cambiar_acceso_ni_relaciones(yo):
    persona = yo.persona
    antes = (persona.whatsapp, persona.email, persona.nivel, persona.sector, persona.lider)
    prohibidos = {
        "whatsapp": "55 9999 9999",
        "email": "otro@correo.com",
        "nivel": "edu",
        "procedencia": "externo",
        "activo": False,
        "sector": "Z",
        "grupo_conexion": "Otro grupo",
        "lider": "Alguien",
        "ministerios": "Cafetería",
        "sirve_en_ministerio": True,
        "otros_cursos": "Todos",
        "observaciones": "Nota",
        "usuario": 1,
    }
    r = api_de(yo).patch(URL, {**prohibidos, "colonia": "Condesa"}, format="json")
    assert r.status_code == 200
    persona.refresh_from_db()
    assert (persona.whatsapp, persona.email, persona.nivel, persona.sector, persona.lider) == antes
    assert persona.activo and persona.procedencia != "externo" and persona.ministerios == ""
    assert persona.colonia == "Condesa"
    yo.refresh_from_db()
    assert yo.whatsapp == persona.whatsapp and yo.email == ""
    # y su grupo de conexión sigue igual
    assert GrupoMiembro.objects.filter(persona=persona, activo=True).count() == 1


def test_el_nombre_no_puede_quedar_vacio(yo):
    assert api_de(yo).patch(URL, {"nombre": "  "}, format="json").status_code == 400


def test_se_requiere_sesion_y_cada_quien_edita_solo_lo_suyo(yo):
    assert APIClient().patch(URL, {"colonia": "X"}, format="json").status_code in (401, 403)
    otro = User.objects.create_user("55 0000 0101", pin=PIN, nombre="Otro")
    api_de(otro).patch(URL, {"colonia": "Otra"}, format="json")
    assert api_de(yo).get(URL).json()["colonia"] == ""


def test_la_foto_exige_aceptar_su_uso_y_lo_registra(yo, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    sin = api_de(yo).post(URL + "foto/", {"foto": png()}, format="multipart")
    assert sin.status_code == 400 and sin.json()["code"] == "consent_required"
    con = api_de(yo).post(URL + "foto/", {"foto": png(), "acepta_foto": True}, format="multipart")
    assert con.status_code == 200 and con.json()["tiene_foto"] and con.json()["acepto_foto"]
    assert Consentimiento.objects.filter(persona=yo.persona, acepta_foto=True).count() == 1
    # con el consentimiento ya dado, cambiarla no lo vuelve a pedir
    otra = api_de(yo).post(URL + "foto/", {"foto": png()}, format="multipart")
    assert otra.status_code == 200
    assert Consentimiento.objects.filter(persona=yo.persona).count() == 1
    assert api_de(yo).get(URL + "foto/").status_code == 200
