"""El aviso de privacidad se sustituye desde la aplicación, sin tocar el código."""

from rest_framework.test import APIClient

from apps.accounts.models import AsignacionRol, Rol, User
from apps.core.models import AuditEvent

from . import aviso
from .models import AvisoPrivacidad, Consentimiento
from .test_perfil import PIN, api_de, yo  # noqa: F401

URL = "/api/personas/aviso-privacidad/"
TEXTO = "Aviso oficial de Mundo de Fe México. " * 5


def admin(clave="pastor"):
    user = User.objects.create_user("55 0000 0200", pin=PIN, nombre="Admin")
    AsignacionRol.objects.create(usuario=user, rol=Rol.objects.get(clave=clave))
    return user


def test_sin_publicar_rige_el_provisional(db):
    datos = APIClient().get(URL).json()
    assert datos["version"] == aviso.VERSION_PROVISIONAL
    assert "PROVISIONAL" in datos["texto"] and "vehículo" in datos["texto"]


def test_solo_quien_administra_la_configuracion_publica(yo):  # noqa: F811
    cuerpo = {"version": "1.0", "texto": TEXTO}
    assert api_de(yo).post(URL + "publicar/", cuerpo, format="json").status_code == 403
    assert APIClient().post(URL + "publicar/", cuerpo, format="json").status_code in (401, 403)
    r = api_de(admin("admin_tecnico")).post(URL + "publicar/", cuerpo, format="json")
    assert r.status_code == 201 and r.json()["version"] == "1.0"
    assert AuditEvent.objects.filter(action="aviso.publicado").exists()


def test_la_version_nueva_es_la_vigente_y_no_se_repite(yo):  # noqa: F811
    jefe = api_de(admin("secretaria"))
    assert (
        jefe.post(URL + "publicar/", {"version": "1.0", "texto": TEXTO}, format="json").status_code
        == 201
    )
    assert APIClient().get(URL).json()["texto"] == TEXTO.strip()
    repetida = jefe.post(URL + "publicar/", {"version": "1.0", "texto": TEXTO}, format="json")
    assert repetida.status_code == 400
    corto = jefe.post(URL + "publicar/", {"version": "1.1", "texto": "hola"}, format="json")
    assert corto.status_code == 400
    assert AvisoPrivacidad.objects.count() == 1


def test_quien_aceptó_otra_versión_debe_aceptar_la_nueva(yo):  # noqa: F811
    persona = yo.persona
    Consentimiento.objects.create(
        persona=persona, version="0.2-provisional", acepta_datos=True, acepta_foto=True
    )
    assert api_de(yo).get("/api/personas/mi-perfil/").json()["aviso_pendiente"] is False
    api_de(admin()).post(URL + "publicar/", {"version": "1.0", "texto": TEXTO}, format="json")
    assert api_de(yo).get("/api/personas/mi-perfil/").json()["aviso_pendiente"] is True
    r = api_de(yo).post("/api/personas/mi-perfil/aceptar-aviso/")
    assert r.status_code == 200 and r.json()["aviso_pendiente"] is False
    ultimo = persona.consentimientos.order_by("-fecha", "-pk").first()
    assert ultimo.version == "1.0" and ultimo.acepta_foto is True  # conserva lo de la foto
