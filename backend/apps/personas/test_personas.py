import io
from datetime import date

import pytest
from django.core.cache import cache
from django.utils import timezone
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


def _con_rol(user, clave):
    from apps.accounts.models import AsignacionRol, Rol

    AsignacionRol.objects.create(usuario=user, rol=Rol.objects.get(clave=clave))
    return user


@pytest.fixture
def staff(db):
    return _con_rol(
        User.objects.create_user("55 9999 0000", pin="482915", nombre="Admin"), "pastor"
    )


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
    assert consentimiento.acepta_datos and consentimiento.version == "0.2-provisional"
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
        {"fecha": timezone.localdate().isoformat(), "motivo": "Se mudó"},
        format="json",
    )
    assert r.status_code == 200 and r.json()["activo"] is False
    mov = api.get(f"/api/personas/{pid}/movimientos/").json()[0]
    assert (
        mov["tipo"] == "baja"
        and mov["motivo"] == "Se mudó"
        and mov["fecha"] == timezone.localdate().isoformat()
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
def test_aviso_de_privacidad_es_publico_y_versionado(
    db,
):
    r = APIClient().get("/api/personas/aviso-privacidad/")
    assert r.status_code == 200
    assert r.json()["version"] == "0.2-provisional" and "PROVISIONAL" in r.json()["texto"]


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


# ---------- roles visibles en el listado y el detalle ----------
def test_el_listado_y_el_detalle_muestran_los_roles_de_la_persona(api, staff):
    con_cuenta = User.objects.create_user("55 7777 0001", pin="482915", nombre="Lupe")
    _con_rol(con_cuenta, "lider")
    persona = Persona.objects.create(nombre="Lupe", whatsapp="55 7777 0001", usuario=con_cuenta)
    sin_cuenta = Persona.objects.create(nombre="Beto", whatsapp="55 7777 0002")
    filas = {f["id"]: f for f in api.get("/api/personas/").json()["results"]}
    assert filas[persona.pk]["roles"] == ["Líder / Maestro"]
    assert filas[sin_cuenta.pk]["roles"] == []
    assert api.get(f"/api/personas/{persona.pk}/").json()["roles"] == ["Líder / Maestro"]


# ---------- traslado a otra iglesia, baja y grupos ----------
def _persona_en_grupo(nombre="Gloria", whatsapp="55 8888 0001"):
    from apps.grupos.models import Grupo, GrupoMiembro

    persona = Persona.objects.create(nombre=nombre, whatsapp=whatsapp)
    grupo = Grupo.objects.create(nombre="Conexión Norte")
    GrupoMiembro.objects.create(grupo=grupo, persona=persona, rol="asistente")
    return persona, grupo


def test_traslado_deja_inactiva_a_la_persona_con_su_destino_y_la_saca_de_sus_grupos(api):
    from apps.grupos.models import GrupoMiembro

    persona, grupo = _persona_en_grupo()
    r = api.post(
        f"/api/personas/{persona.pk}/traslado/",
        {"fecha": "2026-10-20", "iglesia_destino": "Iglesia Vida Nueva", "motivo": "Se mudó"},
        format="json",
    )
    assert r.status_code == 200 and r.json()["activo"] is False
    mov = api.get(f"/api/personas/{persona.pk}/movimientos/").json()[0]
    assert mov["tipo"] == "traslado" and mov["iglesia_destino"] == "Iglesia Vida Nueva"
    assert not GrupoMiembro.objects.get(grupo=grupo, persona=persona).activo
    evento = AuditEvent.objects.get(action="persona.traslado")
    assert evento.detail["destino"] == "Iglesia Vida Nueva"
    assert evento.detail["grupos_quitados"] == [grupo.pk]
    # no se traslada dos veces ni sin destino
    otra = api.post(
        f"/api/personas/{persona.pk}/traslado/",
        {"fecha": "2026-10-20", "iglesia_destino": "X"},
        format="json",
    )
    assert otra.status_code == 400


def test_traslado_exige_destino_y_permiso(api, db):
    persona, _ = _persona_en_grupo("Hugo", "55 8888 0002")
    sin_destino = api.post(
        f"/api/personas/{persona.pk}/traslado/",
        {"fecha": "2026-10-20", "iglesia_destino": "   "},
        format="json",
    )
    assert sin_destino.status_code == 400
    lider = APIClient()
    lider.force_authenticate(
        _con_rol(User.objects.create_user("55 8888 0099", pin="482915", nombre="L"), "lider")
    )
    assert lider.post(f"/api/personas/{persona.pk}/traslado/", {}, format="json").status_code == 403


def test_la_baja_tambien_retira_de_los_grupos(api):
    from apps.grupos.models import GrupoMiembro

    persona, grupo = _persona_en_grupo("Iris", "55 8888 0003")
    assert (
        api.post(
            f"/api/personas/{persona.pk}/baja/",
            {"fecha": "2026-10-20", "motivo": "Ya no asiste"},
            format="json",
        ).status_code
        == 200
    )
    assert not GrupoMiembro.objects.get(grupo=grupo, persona=persona).activo


def test_filtros_por_grupo_y_por_rol_y_grupos_en_el_listado(api):
    persona, grupo = _persona_en_grupo("Julia", "55 8888 0004")
    Persona.objects.create(nombre="Kiko", whatsapp="55 8888 0005")
    cuenta = _con_rol(
        User.objects.create_user("55 8888 0006", pin="482915", nombre="Lalo"), "lider"
    )
    lalo = Persona.objects.create(nombre="Lalo", whatsapp="55 8888 0006", usuario=cuenta)
    nombres = lambda qs: sorted(  # noqa: E731
        f["nombre_completo"] for f in api.get(f"/api/personas/?{qs}").json()["results"]
    )
    assert nombres(f"grupo={grupo.pk}") == ["Julia"]
    assert nombres("rol=lider") == ["Lalo"]
    fila = next(f for f in api.get("/api/personas/").json()["results"] if f["id"] == persona.pk)
    assert fila["grupos"] == ["Conexión Norte"]
    assert lalo.pk


# ---------- la baja desactiva el acceso y la reactivación lo devuelve todo ----------
def _persona_con_cuenta(rol, whatsapp, nombre):
    cuenta = _con_rol(User.objects.create_user(whatsapp, pin="482915", nombre=nombre), rol)
    return Persona.objects.create(nombre=nombre, whatsapp=whatsapp, usuario=cuenta), cuenta


def test_la_baja_desactiva_el_acceso_y_reactivar_regresa_acceso_y_grupos(api):
    from apps.grupos.models import Grupo, GrupoMiembro

    persona, cuenta = _persona_con_cuenta("lider", "55 8888 1001", "Lupe")
    norte = Grupo.objects.create(nombre="Norte")
    sur = Grupo.objects.create(nombre="Sur")
    GrupoMiembro.objects.create(grupo=norte, persona=persona, rol="lider")
    ya_fuera = GrupoMiembro.objects.create(
        grupo=sur, persona=persona, rol="asistente", activo=False
    )

    assert (
        api.post(
            f"/api/personas/{persona.pk}/baja/",
            {"fecha": "2026-10-20", "motivo": "Ya no asiste"},
            format="json",
        ).status_code
        == 200
    )
    cuenta.refresh_from_db()
    assert cuenta.is_active is False
    login = APIClient().post(
        "/api/auth/login/", {"identifier": "55 8888 1001", "credential": "482915"}, format="json"
    )
    assert login.status_code == 400  # no puede entrar mientras esté de baja
    assert AuditEvent.objects.get(action="persona.baja").detail["acceso_desactivado"] is True

    assert api.post(f"/api/personas/{persona.pk}/reactivar/", {}, format="json").status_code == 200
    cuenta.refresh_from_db()
    assert cuenta.is_active is True
    assert GrupoMiembro.objects.get(grupo=norte, persona=persona).activo
    ya_fuera.refresh_from_db()
    assert not ya_fuera.activo  # el que dejó antes de la baja no regresa solo
    entra = APIClient().post(
        "/api/auth/login/", {"identifier": "55 8888 1001", "credential": "482915"}, format="json"
    )
    assert entra.status_code == 200


def test_el_traslado_tambien_desactiva_el_acceso(api):
    persona, cuenta = _persona_con_cuenta("lider", "55 8888 1002", "Mario")
    api.post(
        f"/api/personas/{persona.pk}/traslado/",
        {"fecha": "2026-10-20", "iglesia_destino": "Vida Nueva"},
        format="json",
    )
    cuenta.refresh_from_db()
    assert cuenta.is_active is False


def test_solo_un_superior_da_de_baja_y_nunca_a_si_mismo_ni_a_su_nivel(api, staff):
    # `staff` es Pastor y tiene su propia persona
    yo = Persona.objects.create(nombre="Admin", whatsapp="55 9999 0000", usuario=staff)
    asegurar = api.post(
        f"/api/personas/{yo.pk}/baja/", {"fecha": "2026-10-20", "motivo": "x"}, format="json"
    )
    assert asegurar.status_code == 403
    otro_pastor, _ = _persona_con_cuenta("pastor", "55 8888 1003", "Otro Pastor")
    igual = api.post(
        f"/api/personas/{otro_pastor.pk}/baja/",
        {"fecha": "2026-10-20", "motivo": "x"},
        format="json",
    )
    assert igual.status_code == 403
    assert "superior" in igual.json()["detail"]
    anciano, _ = _persona_con_cuenta("anciano", "55 8888 1004", "Anciano")
    assert (
        api.post(
            f"/api/personas/{anciano.pk}/baja/",
            {"fecha": "2026-10-20", "motivo": "x"},
            format="json",
        ).status_code
        == 200
    )


# ---------- la baja es un permiso de rol, limitado a la gente que cada quien atiende ----------
def _dar_permiso(rol, permiso):
    from apps.accounts.models import Rol

    r = Rol.objects.get(clave=rol)
    r.permisos = sorted({*r.permisos, permiso})
    r.save()


def _baja(user, persona):
    c = APIClient()
    c.force_authenticate(user)
    return c.post(
        f"/api/personas/{persona.pk}/baja/", {"fecha": "2026-10-20", "motivo": "x"}, format="json"
    )


def test_el_lider_da_de_baja_solo_a_la_gente_de_su_grupo_si_el_rol_tiene_el_permiso(db):
    from apps.grupos.models import Grupo, GrupoMiembro

    lider = _con_rol(User.objects.create_user("55 7777 0001", pin="482915", nombre="Lía"), "lider")
    yo = Persona.objects.create(nombre="Lía", whatsapp="55 7777 0001", usuario=lider)
    mi_gente = Persona.objects.create(nombre="Rosa", whatsapp="55 7777 0002")
    ajena = Persona.objects.create(nombre="Sara", whatsapp="55 7777 0003")
    norte = Grupo.objects.create(nombre="Norte")
    sur = Grupo.objects.create(nombre="Sur")
    GrupoMiembro.objects.create(grupo=norte, persona=yo, rol="lider")
    GrupoMiembro.objects.create(grupo=norte, persona=mi_gente, rol="asistente")
    GrupoMiembro.objects.create(grupo=sur, persona=ajena, rol="asistente")
    # sin el permiso en su rol, no puede
    assert _baja(lider, mi_gente).status_code == 403
    _dar_permiso("lider", "personas.baja")
    lider = User.objects.get(pk=lider.pk)  # los permisos se guardan en la instancia
    assert _baja(lider, ajena).status_code == 403  # no es de su grupo
    assert _baja(lider, mi_gente).status_code == 200
