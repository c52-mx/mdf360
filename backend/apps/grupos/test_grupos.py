import io
from datetime import date, timedelta

import pytest
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.accounts.models import AsignacionRol, Rol, User
from apps.core.models import AuditEvent
from apps.personas import services as personas

from .models import Asistencia, Grupo, GrupoMiembro, lunes_de

PIN = "482915"


@pytest.fixture(autouse=True)
def _aislar(settings, tmp_path):
    cache.clear()
    settings.MEDIA_ROOT = tmp_path / "media"


def cuenta(whatsapp, nombre, *roles):
    user = User.objects.create_user(whatsapp, pin=PIN, nombre=nombre)
    for clave in roles:
        AsignacionRol.objects.create(usuario=user, rol=Rol.objects.get(clave=clave))
    personas.ensure_persona_for_user(user)
    return user


def api_de(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


@pytest.fixture
def mundo(db):
    pastor = cuenta("55 0000 0001", "Pastor", "pastor")
    anciano = cuenta("55 0000 0002", "Anciano", "anciano")
    lider = cuenta("55 0000 0003", "Laura Líder", "lider")
    secre = cuenta("55 0000 0004", "Sara Secretaria", "secretario")
    super_ = cuenta("55 0000 0005", "Samuel Supervisor", "supervisor")
    otro = cuenta("55 0000 0006", "Otro Líder", "lider")
    norte = Grupo.objects.create(nombre="Conexión Norte", dia_semana=3)
    sur = Grupo.objects.create(nombre="Conexión Sur", dia_semana=1)
    for g, roles in ((norte, [(lider, "lider"), (secre, "secretario"), (super_, "supervisor")]),
                     (sur, [(otro, "lider"), (super_, "supervisor")])):  # fmt: skip
        for user, rol in roles:
            GrupoMiembro.objects.create(grupo=g, persona=user.persona, rol=rol)
    return dict(pastor=pastor, anciano=anciano, lider=lider, secre=secre, super=super_,
                otro=otro, norte=norte, sur=sur)  # fmt: skip


# ---------- alcance ----------
def test_cada_quien_ve_solo_sus_grupos(mundo):
    nombres = lambda u: sorted(g["nombre"] for g in api_de(u).get("/api/grupos/").json())  # noqa: E731
    assert nombres(mundo["lider"]) == ["Conexión Norte"]
    assert nombres(mundo["otro"]) == ["Conexión Sur"]
    assert nombres(mundo["super"]) == ["Conexión Norte", "Conexión Sur"]
    assert (
        nombres(mundo["pastor"]) == nombres(mundo["anciano"]) == ["Conexión Norte", "Conexión Sur"]
    )
    assert nombres(cuenta("55 0000 0099", "Sin grupo", "miembro")) == []


def test_un_lider_no_abre_el_grupo_de_otro(mundo):
    assert api_de(mundo["lider"]).get(f"/api/grupos/{mundo['sur'].pk}/").status_code == 404
    assert api_de(mundo["lider"]).get(f"/api/grupos/{mundo['norte'].pk}/").status_code == 200


def test_solo_la_administracion_crea_grupos(mundo):
    datos = {"nombre": "Nuevo", "dia_semana": 5, "hora": "19:30"}
    assert api_de(mundo["lider"]).post("/api/grupos/", datos, format="json").status_code == 403
    assert api_de(mundo["anciano"]).post("/api/grupos/", datos, format="json").status_code == 403
    r = api_de(mundo["pastor"]).post("/api/grupos/", datos, format="json")
    assert r.status_code == 201 and r.json()["dia"] == "Sábado"
    lideres = api_de(mundo["pastor"]).post(
        "/api/grupos/", {"nombre": "Líderes", "tipo": "lideres"}, format="json"
    )
    assert lideres.json()["tipo"] == "lideres"


# ---------- integrantes ----------
def test_el_lider_agrega_un_invitado_nuevo_con_consentimiento(mundo):
    api = api_de(mundo["lider"])
    url = f"/api/grupos/{mundo['norte'].pk}/integrantes/"
    sin = api.post(
        url, {"whatsapp": "5511223344", "nombre": "Vecino", "rol": "asistente"}, format="json"
    )
    assert sin.status_code == 400 and sin.json()["code"] == "consent_required"
    ok = api.post(
        url,
        {"whatsapp": "5511223344", "nombre": "Vecino", "rol": "asistente", "acepta_datos": True},
        format="json",
    )
    assert ok.status_code == 201 and ok.json()["invitado"] is True
    # el mismo número no duplica a la persona: se vincula
    api_de(mundo["pastor"]).post(
        f"/api/grupos/{mundo['sur'].pk}/integrantes/",
        {"whatsapp": "55 1122 3344", "rol": "asistente"},
        format="json",
    )
    from apps.personas.models import Persona

    assert Persona.objects.filter(whatsapp="+525511223344").count() == 1


def test_el_lider_no_asigna_roles_reservados(mundo):
    r = api_de(mundo["lider"]).post(
        f"/api/grupos/{mundo['norte'].pk}/integrantes/",
        {"whatsapp": "5599887766", "nombre": "X", "rol": "lider", "acepta_datos": True}, format="json",
    )  # fmt: skip
    assert r.status_code == 403 and r.json()["code"] == "role_not_allowed"


def test_el_secretario_no_gestiona_integrantes(mundo):
    r = api_de(mundo["secre"]).post(
        f"/api/grupos/{mundo['norte'].pk}/integrantes/",
        {"whatsapp": "5599887766", "nombre": "X", "acepta_datos": True}, format="json",
    )  # fmt: skip
    assert r.status_code == 403


def test_quitar_integrante_lo_desactiva(mundo):
    pid = personas.crear_persona(datos={"nombre": "A", "whatsapp": "5511000000"}, acepta_datos=True)
    m = GrupoMiembro.objects.create(grupo=mundo["norte"], persona=pid, rol="asistente")
    r = api_de(mundo["lider"]).delete(f"/api/grupos/{mundo['norte'].pk}/integrantes/{m.pk}/")
    assert r.status_code == 204
    m.refresh_from_db()
    assert not m.activo


# ---------- reuniones y asistencia ----------
def _con_asistentes(mundo, n=2):
    ids = []
    for i in range(n):
        p = personas.crear_persona(
            datos={"nombre": f"Asistente {i}", "whatsapp": f"551100000{i}"}, acepta_datos=True
        )
        GrupoMiembro.objects.create(grupo=mundo["norte"], persona=p, rol="asistente")
        ids.append(p.pk)
    return ids


def test_pasar_lista_el_lider(mundo):
    ids = _con_asistentes(mundo)
    api = api_de(mundo["lider"])
    r = api.post(f"/api/grupos/{mundo['norte'].pk}/reuniones/", {}, format="json")
    assert r.status_code == 201
    rid = r.json()["id"]
    detalle = api.get(f"/api/grupos/reuniones/{rid}/").json()
    assert {p["nombre"] for p in detalle["personas"]} >= {"Asistente 0", "Asistente 1"}
    guardado = api.put(
        f"/api/grupos/reuniones/{rid}/",
        {
            "asistencias": [
                {"persona_id": ids[0], "presente": True},
                {"persona_id": ids[1], "presente": False},
            ],
            "notas": "Buen ambiente",
        },
        format="json",
    )
    assert guardado.status_code == 200 and guardado.json()["presentes"] == 1
    assert Asistencia.objects.filter(reunion_id=rid, presente=True).count() == 1
    assert AuditEvent.objects.filter(action="asistencia.guardada").exists()
    # guardar de nuevo corrige, no duplica
    api.put(
        f"/api/grupos/reuniones/{rid}/",
        {"asistencias": [{"persona_id": ids[1], "presente": True}]},
        format="json",
    )
    assert Asistencia.objects.filter(reunion_id=rid).count() == 2


def test_no_se_pasa_lista_a_alguien_de_otro_grupo(mundo):
    ajeno = personas.crear_persona(
        datos={"nombre": "Ajeno", "whatsapp": "5500000077"}, acepta_datos=True
    )
    api = api_de(mundo["lider"])
    rid = api.post(f"/api/grupos/{mundo['norte'].pk}/reuniones/", {}, format="json").json()["id"]
    r = api.put(
        f"/api/grupos/reuniones/{rid}/",
        {"asistencias": [{"persona_id": ajeno.pk, "presente": True}]},
        format="json",
    )
    assert r.status_code == 400


def test_secretario_captura_hoy_pero_no_ve_el_historial(mundo):
    api = api_de(mundo["secre"])
    gid = mundo["norte"].pk
    hoy = api.post(f"/api/grupos/{gid}/reuniones/", {}, format="json")
    assert hoy.status_code == 201
    rid = hoy.json()["id"]
    assert (
        api.put(f"/api/grupos/reuniones/{rid}/", {"asistencias": []}, format="json").status_code
        == 200
    )
    # no abre reuniones de otro día
    ayer = (date.today() - timedelta(days=3)).isoformat()
    assert (
        api.post(f"/api/grupos/{gid}/reuniones/", {"fecha": ayer}, format="json").status_code == 403
    )
    # el detalle del grupo solo le muestra la de hoy
    assert [r["id"] for r in api.get(f"/api/grupos/{gid}/").json()["reuniones"]] == [rid]
    # una reunión pasada creada por el líder queda fuera de su alcance
    vieja = (
        api_de(mundo["lider"])
        .post(f"/api/grupos/{gid}/reuniones/", {"fecha": ayer}, format="json")
        .json()["id"]
    )
    assert api.get(f"/api/grupos/reuniones/{vieja}/").status_code == 404
    assert (
        api.put(f"/api/grupos/reuniones/{vieja}/", {"asistencias": []}, format="json").status_code
        == 404
    )


def test_supervisor_consulta_pero_no_modifica(mundo):
    rid = (
        api_de(mundo["lider"])
        .post(f"/api/grupos/{mundo['norte'].pk}/reuniones/", {}, format="json")
        .json()["id"]
    )
    sup = api_de(mundo["super"])
    ver = sup.get(f"/api/grupos/reuniones/{rid}/")
    assert ver.status_code == 200 and ver.json()["puede_modificar"] is False
    assert (
        sup.put(f"/api/grupos/reuniones/{rid}/", {"asistencias": []}, format="json").status_code
        == 403
    )
    assert (
        sup.post(f"/api/grupos/{mundo['norte'].pk}/reuniones/", {}, format="json").status_code
        == 403
    )


def test_una_reunion_por_grupo_y_fecha(mundo):
    api = api_de(mundo["lider"])
    url = f"/api/grupos/{mundo['norte'].pk}/reuniones/"
    a = api.post(url, {}, format="json").json()["id"]
    assert api.post(url, {}, format="json").json()["id"] == a


# ---------- estudio semanal ----------
def pdf(nombre="estudio.pdf", peso=0):
    return SimpleUploadedFile(nombre, b"%PDF-1.4\n" + b"0" * peso, content_type="application/pdf")


def audio(nombre="lectura.mp3", peso=2048):
    return SimpleUploadedFile(nombre, b"ID3" + b"0" * peso, content_type="audio/mpeg")


def test_solo_pastor_y_anciano_suben_el_estudio(mundo):
    def datos():  # un archivo nuevo por petición: el anterior ya quedó leído
        return {"titulo": "Lección 1", "semana": date.today().isoformat(), "pdf_adultos": pdf()}

    assert (
        api_de(mundo["lider"])
        .post("/api/grupos/estudios/", datos(), format="multipart")
        .status_code
        == 403
    )
    r = api_de(mundo["anciano"]).post("/api/grupos/estudios/", datos(), format="multipart")
    assert r.status_code == 201 and r.json()["pdf_adultos"] and not r.json()["pdf_ninos"]
    assert r.json()["semana"] == lunes_de(date.today()).isoformat()


def test_validaciones_de_archivos(mundo):
    api = api_de(mundo["pastor"])
    base = {"titulo": "X", "semana": date.today().isoformat()}
    falso = SimpleUploadedFile("malo.pdf", b"no soy pdf")
    assert (
        api.post(
            "/api/grupos/estudios/", {**base, "pdf_adultos": falso}, format="multipart"
        ).status_code
        == 400
    )
    exe = SimpleUploadedFile("a.exe", b"%PDF-1.4")
    assert (
        api.post(
            "/api/grupos/estudios/", {**base, "pdf_ninos": exe}, format="multipart"
        ).status_code
        == 400
    )
    assert (
        api.post(
            "/api/grupos/estudios/",
            {**base, "audio": SimpleUploadedFile("a.txt", b"x")},
            format="multipart",
        ).status_code
        == 400
    )
    assert (
        api.post("/api/grupos/estudios/", {**base, "titulo": ""}, format="multipart").status_code
        == 400
    )


def test_el_lider_lee_el_estudio_de_la_semana_en_la_reunion(mundo):
    api_de(mundo["pastor"]).post(
        "/api/grupos/estudios/",
        {"titulo": "Lección 2", "semana": date.today().isoformat(), "pdf_adultos": pdf(), "pdf_ninos": pdf("ninos.pdf"), "audio": audio()},
        format="multipart",
    )  # fmt: skip
    lider = api_de(mundo["lider"])
    rid = lider.post(f"/api/grupos/{mundo['norte'].pk}/reuniones/", {}, format="json").json()["id"]
    estudio = lider.get(f"/api/grupos/reuniones/{rid}/").json()["estudio"]
    assert estudio["titulo"] == "Lección 2"
    assert all(estudio[k] for k in ("pdf_adultos", "pdf_ninos", "audio"))
    descarga = lider.get(estudio["pdf_adultos"])
    assert descarga.status_code == 200 and descarga["Content-Type"] == "application/pdf"
    assert b"".join(descarga.streaming_content).startswith(b"%PDF-")


def test_el_audio_admite_rangos(mundo):
    r = api_de(mundo["pastor"]).post(
        "/api/grupos/estudios/",
        {"titulo": "A", "semana": date.today().isoformat(), "audio": audio(peso=997)},
        format="multipart",
    )
    url = r.json()["audio"]
    lider = api_de(mundo["lider"])
    completo = lider.get(url)
    assert completo["Content-Type"] == "audio/mpeg" and completo["Accept-Ranges"] == "bytes"
    parcial = lider.get(url, HTTP_RANGE="bytes=0-9")
    assert parcial.status_code == 206 and parcial["Content-Range"] == "bytes 0-9/1000"
    assert len(b"".join(parcial.streaming_content)) == 10
    cola = lider.get(url, HTTP_RANGE="bytes=-5")
    assert cola.status_code == 206 and cola["Content-Range"] == "bytes 995-999/1000"
    assert lider.get(url, HTTP_RANGE="bytes=5000-").status_code == 416


def test_sin_grupo_no_ve_los_estudios(mundo):
    api_de(mundo["pastor"]).post(
        "/api/grupos/estudios/",
        {"titulo": "A", "semana": date.today().isoformat(), "pdf_adultos": pdf()},
        format="multipart",
    )
    simple = api_de(cuenta("55 0000 0098", "Miembro", "miembro"))
    assert simple.get("/api/grupos/estudios/").status_code == 403
    assert api_de(mundo["lider"]).get("/api/grupos/estudios/").status_code == 200
    assert APIClient().get("/api/grupos/estudios/").status_code == 403


def test_archivo_inexistente(mundo):
    assert api_de(mundo["pastor"]).get("/api/grupos/estudios/999/archivo/audio/").status_code == 404
    assert api_de(mundo["pastor"]).get("/api/grupos/estudios/1/archivo/otro/").status_code == 404


def test_permiso_nuevo_en_roles(db):
    assert "grupos.gestionar" in Rol.objects.get(clave="pastor").permisos
    assert "grupos.material" in Rol.objects.get(clave="anciano").permisos
    assert "grupos.gestionar" not in Rol.objects.get(clave="anciano").permisos


_ = io  # noqa: F841
