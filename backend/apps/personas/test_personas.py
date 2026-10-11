import io
from datetime import date

import pytest
from django.core.cache import cache
from PIL import Image
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.core.models import AuditEvent

from . import services
from .models import Consentimiento, Nivel, Persona, PersonaMovimiento, ProcesoDiscipular

ALTA = {
    "nombre": "María",
    "apellido_paterno": "López",
    "whatsapp": "55 4444 3333",
    "procedencia": "invitado_grupo",
    "acepta_datos": True,
}


@pytest.fixture(autouse=True)
def _aislar(settings, tmp_path):
    cache.clear()
    settings.MEDIA_ROOT = tmp_path / "media"


@pytest.fixture
def staff(db):
    return User.objects.create_user("55 9999 0000", pin="482915", nombre="Admin", is_staff=True)


@pytest.fixture
def api(staff):
    client = APIClient()
    client.force_authenticate(staff)
    return client


def alta(api, **cambios):
    return api.post("/api/personas/", {**ALTA, **cambios}, format="json")


def png_bytes(lado=1600):
    buffer = io.BytesIO()
    Image.new("RGB", (lado, lado // 2), "purple").save(buffer, "PNG")
    buffer.seek(0)
    buffer.name = "foto.png"
    return buffer


# ---------- permisos ----------
def test_solo_personal_autorizado(db):
    assert APIClient().get("/api/personas/").status_code == 403
    comun = User.objects.create_user("55 1212 3434", pin="482915", nombre="Comun")
    cliente = APIClient()
    cliente.force_authenticate(comun)
    assert cliente.get("/api/personas/").status_code == 403


# ---------- alta de contacto ----------
def test_alta_rapida_crea_contacto_con_consentimiento_y_movimiento(api):
    r = alta(api)
    assert r.status_code == 201
    body = r.json()
    assert body["nivel"] == "contacto" and body["whatsapp"] == "+525544443333"
    persona = Persona.objects.get(pk=body["id"])
    consentimiento = Consentimiento.objects.get(persona=persona)
    assert consentimiento.acepta_datos and consentimiento.version == "0.1-generico"
    assert persona.movimientos.filter(tipo="alta").exists()
    assert AuditEvent.objects.filter(action="persona.created", target_id=str(persona.pk)).exists()


def test_alta_sin_consentimiento_se_rechaza(api):
    r = alta(api, acepta_datos=False)
    assert r.status_code == 400 and r.json()["code"] == "consent_required"
    assert Persona.objects.count() == 0


def test_whatsapp_duplicado_devuelve_la_persona_existente(api):
    primera = alta(api).json()
    r = alta(api, whatsapp="+52 (55) 4444-3333", nombre="Otra")
    assert r.status_code == 409
    assert r.json()["code"] == "duplicate" and r.json()["persona_id"] == primera["id"]
    assert Persona.objects.count() == 1


def test_whatsapp_invalido(api):
    assert alta(api, whatsapp="123").status_code == 400


# ---------- lista y búsqueda ----------
def test_busqueda_por_nombre_y_por_numero(api):
    alta(api)
    alta(api, nombre="Pedro", apellido_paterno="Ruiz", whatsapp="5511119999")
    assert api.get("/api/personas/?q=lopez").json()["count"] == 1  # sin importar acentos
    assert api.get("/api/personas/?q=LÓPEZ").json()["count"] == 1
    assert api.get("/api/personas/?q=maría lópez").json()["count"] == 1
    assert api.get("/api/personas/?q=4444").json()["count"] == 1
    assert api.get("/api/personas/?nivel=edu").json()["count"] == 0
    assert api.get("/api/personas/").json()["count"] == 2


# ---------- ficha y radiografía ----------
def test_ficha_con_los_campos_de_la_radiografia(api):
    pid = alta(api).json()["id"]
    r = api.patch(
        f"/api/personas/{pid}/",
        {
            "apellido_materno": "Pérez",
            "fecha_nacimiento": "1990-05-20",
            "calle_numero": "Reforma 100",
            "colonia": "Centro",
            "codigo_postal": "06000",
            "alcaldia": "Cuauhtémoc",
            "telefono_fijo": "5555550000",
            "email": "Maria@Example.com",
            "sector": "Norte",
            "grupo_conexion": "Conexión Norte",
            "lider": "Laura Pérez",
            "sirve_en_ministerio": True,
            "ministerios": "Alabanza",
            "oracion_familias": True,
            "devocional_personal": "Diario",
            "otros_cursos": "Finanzas",
            "observaciones": "Ninguna",
        },
        format="json",
    )
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "maria@example.com"
    assert body["edad"] == services.Persona(fecha_nacimiento=date(1990, 5, 20)).edad
    assert body["nombre_completo"] == "María López Pérez"
    evento = AuditEvent.objects.filter(action="persona.updated").latest("created_at")
    assert "fecha_nacimiento" in evento.detail["campos"]
    assert "1990" not in str(evento.detail)  # la bitácora guarda los campos, no los valores


def test_no_se_puede_cambiar_el_nivel_ni_el_estado_con_patch(api):
    pid = alta(api).json()["id"]
    api.patch(f"/api/personas/{pid}/", {"nivel": "edu", "activo": False}, format="json")
    persona = Persona.objects.get(pk=pid)
    assert persona.nivel == "contacto" and persona.activo


def test_cambiar_whatsapp_a_uno_existente_se_rechaza(api):
    alta(api)
    otro = alta(api, nombre="Pedro", whatsapp="5511119999").json()["id"]
    r = api.patch(f"/api/personas/{otro}/", {"whatsapp": "5544443333"}, format="json")
    assert r.status_code == 400


def test_consultar_la_ficha_queda_en_bitacora(api):
    pid = alta(api).json()["id"]
    api.get(f"/api/personas/{pid}/")
    assert AuditEvent.objects.filter(action="persona.viewed", target_id=str(pid)).exists()


# ---------- niveles ----------
def test_ascenso_a_expediente_completo_exige_datos_minimos(api):
    pid = alta(api).json()["id"]
    assert (
        api.post(
            f"/api/personas/{pid}/nivel/", {"nivel": "participante"}, format="json"
        ).status_code
        == 200
    )
    r = api.post(f"/api/personas/{pid}/nivel/", {"nivel": "edu"}, format="json")
    assert r.status_code == 400 and "fecha de nacimiento" in r.json()["detail"]
    api.patch(f"/api/personas/{pid}/", {"fecha_nacimiento": "1990-05-20"}, format="json")
    r = api.post(f"/api/personas/{pid}/nivel/", {"nivel": "edu"}, format="json")
    assert r.status_code == 200 and r.json()["nivel"] == "edu"
    assert PersonaMovimiento.objects.filter(persona_id=pid, tipo="cambio_nivel").count() == 2


def test_el_nivel_solo_avanza(api):
    pid = alta(api).json()["id"]
    api.post(f"/api/personas/{pid}/nivel/", {"nivel": "participante"}, format="json")
    r = api.post(f"/api/personas/{pid}/nivel/", {"nivel": "participante"}, format="json")
    assert r.status_code == 400


# ---------- baja ----------
def test_baja_registra_fecha_y_motivo_y_sale_de_la_lista(api):
    pid = alta(api).json()["id"]
    r = api.post(
        f"/api/personas/{pid}/baja/",
        {"fecha": date.today().isoformat(), "motivo": "Se mudó"},
        format="json",
    )
    assert r.status_code == 200 and r.json()["activo"] is False
    mov = api.get(f"/api/personas/{pid}/movimientos/").json()[0]
    assert (
        mov["tipo"] == "baja"
        and mov["motivo"] == "Se mudó"
        and mov["fecha"] == date.today().isoformat()
    )
    assert api.get("/api/personas/").json()["count"] == 0
    assert api.get("/api/personas/?activo=all").json()["count"] == 1
    assert (
        api.post(
            f"/api/personas/{pid}/baja/", {"fecha": "2026-10-02", "motivo": "x"}, format="json"
        ).status_code
        == 400
    )
    assert api.post(f"/api/personas/{pid}/reactivar/", {}, format="json").status_code == 200
    assert api.get("/api/personas/").json()["count"] == 1


# ---------- procesos discipulares ----------
def test_catalogo_sembrado_con_los_procesos_de_la_hoja(api):
    nombres = [p["nombre"] for p in api.get("/api/personas/catalogo/procesos/").json()]
    assert len(nombres) == 14
    assert nombres[0] == "Nacimiento Espiritual" and nombres[-1] == "Lanzamiento"
    assert "Panorama Bíblico" in nombres


def test_guardar_avance_en_procesos(api):
    pid = alta(api).json()["id"]
    peniel = ProcesoDiscipular.objects.get(nombre="Peniel")
    panorama = ProcesoDiscipular.objects.get(nombre="Panorama Bíblico")
    r = api.post(
        f"/api/personas/{pid}/procesos/",
        [
            {"proceso": peniel.pk, "completado": True, "fecha": "2025-03-01"},
            {
                "proceso": panorama.pk,
                "completado": True,
                "fecha": "2025-06-10",
                "maestro": "Pastor Juan",
            },
        ],
        format="json",
    )
    assert r.status_code == 200
    filas = {f["nombre"]: f for f in r.json()["procesos"]}
    assert filas["Peniel"]["completado"] and filas["Peniel"]["fecha"] == "2025-03-01"
    assert filas["Panorama Bíblico"]["maestro"] == "Pastor Juan"
    assert not filas["Sanidad Total"]["completado"]
    # guardar de nuevo actualiza, no duplica
    api.post(
        f"/api/personas/{pid}/procesos/",
        [{"proceso": peniel.pk, "completado": False}],
        format="json",
    )
    assert Persona.objects.get(pk=pid).procesos.count() == 2


# ---------- foto ----------
def test_foto_se_reduce_y_solo_se_sirve_con_permiso(api, settings):
    pid = alta(api).json()["id"]
    r = api.post(f"/api/personas/{pid}/foto/", {"foto": png_bytes()}, format="multipart")
    assert r.status_code == 200 and r.json()["tiene_foto"]
    persona = Persona.objects.get(pk=pid)
    assert persona.foto.name.startswith(f"personas/{pid}/")  # la ruta queda en la base de datos
    assert (settings.MEDIA_ROOT / persona.foto.name).exists()  # y el archivo, en la carpeta
    descarga = api.get(f"/api/personas/{pid}/foto/")
    assert descarga.status_code == 200 and descarga["Content-Type"] == "image/jpeg"
    imagen = Image.open(io.BytesIO(b"".join(descarga.streaming_content)))
    assert max(imagen.size) <= 800
    assert APIClient().get(f"/api/personas/{pid}/foto/").status_code == 403


def test_archivo_que_no_es_imagen_se_rechaza(api):
    pid = alta(api).json()["id"]
    falso = io.BytesIO(b"no soy una imagen")
    falso.name = "foto.png"
    r = api.post(f"/api/personas/{pid}/foto/", {"foto": falso}, format="multipart")
    assert r.status_code == 400


def test_sin_foto_responde_404(api):
    pid = alta(api).json()["id"]
    assert api.get(f"/api/personas/{pid}/foto/").status_code == 404


# ---------- aviso de privacidad ----------
def test_aviso_de_privacidad_es_publico_y_versionado():
    r = APIClient().get("/api/personas/aviso-privacidad/")
    assert r.status_code == 200
    assert r.json()["version"] == "0.1-generico" and "GENÉRICO" in r.json()["texto"]


# ---------- integración con cuentas ----------
def test_invitar_crea_o_enlaza_la_persona(api, staff):
    existente = Persona.objects.create(nombre="Pedro", whatsapp="5577770000")
    r = api.post(
        "/api/auth/invitations/", {"whatsapp": "5577770000", "nombre": "Pedro Gómez"}, format="json"
    )
    assert r.status_code == 201
    existente.refresh_from_db()
    assert existente.usuario.whatsapp == "+525577770000"
    nueva = api.post(
        "/api/auth/invitations/", {"whatsapp": "5588880000", "nombre": "Ana Ruiz"}, format="json"
    )
    assert nueva.status_code == 201
    assert Persona.objects.get(whatsapp="+525588880000").usuario is not None


def test_la_activacion_exige_aceptar_el_aviso_y_registra_el_consentimiento(api):
    r = api.post(
        "/api/auth/invitations/", {"whatsapp": "5588880000", "nombre": "Ana Ruiz"}, format="json"
    )
    token = r.json()["activation_url"].rsplit("/", 1)[1]
    cliente = APIClient()
    sin = cliente.post(
        "/api/auth/activation/complete/",
        {"token": token, "credential": "482915", "acepta_privacidad": False},
        format="json",
    )
    assert sin.status_code == 400 and sin.json()["code"] == "consent_required"
    con = cliente.post(
        "/api/auth/activation/complete/",
        {"token": token, "credential": "482915", "acepta_privacidad": True, "acepta_foto": True},
        format="json",
    )
    assert con.status_code == 200
    consentimiento = Consentimiento.objects.get(persona__whatsapp="+525588880000")
    assert consentimiento.acepta_foto and consentimiento.registrado_por.nombre == "Ana Ruiz"


def test_nivel_por_defecto_es_contacto():
    assert Persona(nombre="x").nivel == Nivel.CONTACTO
