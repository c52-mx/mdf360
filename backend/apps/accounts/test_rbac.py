import pytest
from rest_framework.test import APIClient

from apps.core.models import AuditEvent

from .models import AsignacionRol, Rol, User

PIN = "482915"


def usuario(whatsapp, *roles, nombre="Persona"):
    user = User.objects.create_user(whatsapp, pin=PIN, nombre=nombre)
    for clave in roles:
        AsignacionRol.objects.create(usuario=user, rol=Rol.objects.get(clave=clave))
    return user


def cliente(user):
    api = APIClient()
    api.force_authenticate(user)
    return api


@pytest.fixture
def pastor(db):
    return usuario("55 0000 0001", "pastor", nombre="Pastor")


def test_catalogo_sembrado(db):
    assert Rol.objects.count() == 11  # incluye Equipo de oración y Secretaria
    assert "bitacora.ver" in Rol.objects.get(clave="admin_tecnico").permisos
    assert Rol.objects.get(clave="tesorero").exige_credencial_fuerte


def test_sin_rol_no_ve_personas(db):
    api = cliente(usuario("55 0000 0002", "miembro"))
    assert api.get("/api/personas/").status_code == 403
    assert (
        api.post(
            "/api/auth/invitations/", {"whatsapp": "5511110000", "nombre": "X"}, format="json"
        ).status_code
        == 403
    )


def test_matriz_admin_tecnico_no_ve_expedientes(db):
    admin = cliente(usuario("55 0000 0003", "admin_tecnico"))
    assert admin.get("/api/personas/").status_code == 403  # matriz: EDU sin acceso
    assert admin.get("/api/auth/roles/").status_code == 200
    assert (
        admin.post(
            "/api/auth/invitations/", {"whatsapp": "5511110000", "nombre": "X"}, format="json"
        ).status_code
        == 201
    )


def test_pastor_ve_y_edita(pastor):
    api = cliente(pastor)
    assert api.get("/api/personas/").status_code == 200
    r = api.post(
        "/api/personas/",
        {"nombre": "A", "whatsapp": "5511112222", "acepta_datos": True},
        format="json",
    )
    assert r.status_code == 201
    pid = r.json()["id"]
    assert (
        api.patch(f"/api/personas/{pid}/", {"colonia": "Centro"}, format="json").status_code == 200
    )
    assert (
        api.post(
            f"/api/personas/{pid}/baja/", {"fecha": "2026-10-01", "motivo": "x"}, format="json"
        ).status_code
        == 200
    )


def test_anciano_ve_y_edita_pero_no_da_de_baja(pastor):
    api = cliente(usuario("55 0000 0004", "anciano"))
    pid = (
        cliente(pastor)
        .post(
            "/api/personas/",
            {"nombre": "A", "whatsapp": "5511112222", "acepta_datos": True},
            format="json",
        )
        .json()["id"]
    )
    assert api.get(f"/api/personas/{pid}/").status_code == 200
    assert (
        api.patch(f"/api/personas/{pid}/", {"colonia": "Centro"}, format="json").status_code == 200
    )
    assert (
        api.post(
            f"/api/personas/{pid}/baja/", {"fecha": "2026-10-01", "motivo": "x"}, format="json"
        ).status_code
        == 403
    )


def test_lider_registra_contactos_pero_no_lee_el_directorio(pastor):
    lider = cliente(usuario("55 0000 0005", "lider"))
    assert (
        lider.post(
            "/api/personas/",
            {"nombre": "B", "whatsapp": "5522223333", "acepta_datos": True},
            format="json",
        ).status_code
        == 201
    )
    assert lider.get("/api/personas/").status_code == 403
    assert (
        lider.post(
            "/api/auth/invitations/", {"whatsapp": "5544445555", "nombre": "Y"}, format="json"
        ).status_code
        == 201
    )


def test_me_incluye_roles_y_permisos(pastor):
    datos = cliente(pastor).get("/api/auth/me/").json()
    assert datos["roles"] == ["pastor"] and "personas.ver" in datos["permisos"]


def test_asignar_roles_marca_credencial_fuerte_y_audita(pastor):
    persona = usuario("55 0000 0006", nombre="Tere")
    r = cliente(pastor).post(
        f"/api/auth/users/{persona.pk}/roles/", {"roles": ["tesorero", "lider"]}, format="json"
    )
    assert r.status_code == 200 and sorted(r.json()["roles"]) == ["lider", "tesorero"]
    persona.refresh_from_db()
    assert persona.requires_strong_credential
    assert AuditEvent.objects.filter(
        action="rbac.roles_changed", target_id=str(persona.pk)
    ).exists()
    # al quitarle el rol sensible deja de exigirse
    cliente(pastor).post(
        f"/api/auth/users/{persona.pk}/roles/", {"roles": ["lider"]}, format="json"
    )
    persona.refresh_from_db()
    assert not persona.requires_strong_credential


def test_nadie_otorga_un_rol_mas_alto_que_el_suyo(db):
    admin = usuario("55 0000 0007", "admin_tecnico")
    otro = usuario("55 0000 0008")
    api = cliente(admin)
    assert (
        api.post(
            f"/api/auth/users/{otro.pk}/roles/", {"roles": ["pastor"]}, format="json"
        ).status_code
        == 200
    )  # nivel 1 > 0
    pastor_ = usuario("55 0000 0009", "pastor")
    api = cliente(pastor_)
    r = api.post(f"/api/auth/users/{otro.pk}/roles/", {"roles": ["admin_tecnico"]}, format="json")
    assert r.status_code == 403 and r.json()["code"] == "role_not_allowed"


def test_rol_inexistente(pastor):
    otro = usuario("55 0000 0010")
    r = cliente(pastor).post(
        f"/api/auth/users/{otro.pk}/roles/", {"roles": ["dios"]}, format="json"
    )
    assert r.status_code == 400


def test_usuario_inactivo_pierde_permisos(pastor):
    pastor.is_active = False
    pastor.save()
    assert pastor.permisos() == set()


# ---------- administrador de roles y permisos ----------
def _secretaria():
    return usuario("55 0000 0020", "secretaria")


def test_la_secretaria_es_como_el_pastor_y_ambos_administran_roles(db):
    pastor_ = Rol.objects.get(clave="pastor")
    secretaria = Rol.objects.get(clave="secretaria")
    assert set(secretaria.permisos) == set(pastor_.permisos)
    assert secretaria.nivel == pastor_.nivel == 1
    assert "roles.administrar" in pastor_.permisos
    assert "roles.administrar" in Rol.objects.get(clave="admin_tecnico").permisos
    assert "roles.administrar" not in Rol.objects.get(clave="anciano").permisos


def test_el_catalogo_cubre_todos_los_permisos_del_sistema(db):
    from . import catalogo
    from .roles import PERMISOS

    assert catalogo.codigos() == set(PERMISOS)


def test_crear_un_rol_con_permisos_de_la_matriz(db):
    api = cliente(_secretaria())
    r = api.post(
        "/api/auth/roles/",
        {
            "nombre": "Encargado de cafetería",
            "descripcion": "Atiende la cafetería",
            "nivel": 6,
            "permisos": ["personas.crear"],
        },
        format="json",
    )
    assert r.status_code == 201
    assert r.json()["clave"] == "encargado-de-cafeteria" and r.json()["editable"] is True
    assert AuditEvent.objects.filter(action="rbac.rol_creado").exists()
    repetido = api.post(
        "/api/auth/roles/",
        {"nombre": "encargado de cafetería", "nivel": 6, "permisos": []},
        format="json",
    )
    assert repetido.status_code == 400


def test_nadie_crea_un_rol_igual_o_mas_alto_que_el_suyo(db):
    api = cliente(_secretaria())
    for nivel in (0, 1):
        r = api.post(
            "/api/auth/roles/",
            {"nombre": f"Alto {nivel}", "nivel": nivel, "permisos": []},
            format="json",
        )
        assert r.status_code == 400 and "por debajo de tu nivel" in r.json()["detail"]


def _coordinacion():
    rol = Rol.objects.create(
        clave="coordinacion",
        nombre="Coordinación",
        nivel=3,
        permisos=["roles.administrar", "roles.gestionar", "personas.crear"],
    )
    user = usuario("55 0000 0021")
    AsignacionRol.objects.create(usuario=user, rol=rol)
    return user


def test_nadie_concede_permisos_que_no_tiene(db):
    api = cliente(_coordinacion())
    r = api.post(
        "/api/auth/roles/",
        {"nombre": "Curioso", "nivel": 5, "permisos": ["personas.ver"]},
        format="json",
    )
    assert r.status_code == 400 and "personas.ver" in r.json()["detail"]
    permitido = api.post(
        "/api/auth/roles/",
        {"nombre": "Permitido", "nivel": 5, "permisos": ["personas.crear"]},
        format="json",
    )
    assert permitido.status_code == 201


def test_permisos_inventados_se_rechazan(db):
    r = cliente(_secretaria()).post(
        "/api/auth/roles/",
        {"nombre": "Raro", "nivel": 5, "permisos": ["nave.espacial"]},
        format="json",
    )
    assert r.status_code == 400 and "nave.espacial" in r.json()["detail"]


def test_el_rol_del_super_usuario_no_se_toca_ni_se_copia(db):
    api = cliente(_secretaria())
    quitar = {"permisos": []}
    assert api.patch("/api/auth/roles/admin_tecnico/", quitar, format="json").status_code == 403
    assert api.post("/api/auth/roles/admin_tecnico/duplicar/", {}, format="json").status_code == 403
    assert (
        api.post("/api/auth/roles/admin_tecnico/desactivar/", {}, format="json").status_code == 403
    )
    # ni el propio Super Usuario: así nadie se deja fuera del sistema
    admin = cliente(usuario("55 0000 0022", "admin_tecnico"))
    assert admin.patch("/api/auth/roles/admin_tecnico/", quitar, format="json").status_code == 403


def test_la_secretaria_no_edita_el_rol_del_pastor_pero_el_super_usuario_si(db):
    quitar = {
        "permisos": [p for p in Rol.objects.get(clave="pastor").permisos if p != "bitacora.ver"]
    }
    assert (
        cliente(_secretaria()).patch("/api/auth/roles/pastor/", quitar, format="json").status_code
        == 403
    )
    # el Super Usuario no tiene todos los permisos del Pastor: solo puede quitar, nunca agregar
    admin = cliente(usuario("55 0000 0023", "admin_tecnico"))
    r = admin.patch("/api/auth/roles/pastor/", quitar, format="json")
    assert r.status_code == 200 and "bitacora.ver" not in r.json()["permisos"]
    evento = AuditEvent.objects.filter(action="rbac.rol_editado").latest("id")
    assert evento.detail["quitados"] == ["bitacora.ver"]


def test_exigir_credencial_fuerte_marca_a_quienes_ya_tienen_el_rol(db):
    rol = Rol.objects.create(clave="tarjeta", nombre="Tarjeta", nivel=5, permisos=[])
    persona_ = usuario("55 0000 0024")
    AsignacionRol.objects.create(usuario=persona_, rol=rol)
    assert persona_.requires_strong_credential is False
    r = cliente(_secretaria()).patch(
        "/api/auth/roles/tarjeta/", {"exige_credencial_fuerte": True}, format="json"
    )
    assert r.status_code == 200
    persona_.refresh_from_db()
    assert persona_.requires_strong_credential is True


def test_duplicar_un_rol_copia_solo_lo_que_se_puede_conceder(db):
    Rol.objects.create(
        clave="origen",
        nombre="Origen",
        nivel=4,
        permisos=["personas.crear", "personas.ver", "bitacora.ver"],
    )
    r = cliente(_coordinacion()).post("/api/auth/roles/origen/duplicar/", {}, format="json")
    assert r.status_code == 201
    assert r.json()["nombre"] == "Copia de Origen"
    assert r.json()["permisos"] == ["personas.crear"]
    assert Rol.objects.get(clave="origen").permisos == [
        "personas.crear",
        "personas.ver",
        "bitacora.ver",
    ]


def test_desactivar_roles_base_o_en_uso_se_rechaza(db):
    api = cliente(_secretaria())
    base = api.post("/api/auth/roles/lider/desactivar/", {}, format="json")
    assert base.status_code == 400 and "rol base" in base.json()["detail"]
    rol = Rol.objects.create(clave="temporal", nombre="Temporal", nivel=6, permisos=[])
    AsignacionRol.objects.create(usuario=usuario("55 0000 0026"), rol=rol)
    en_uso = api.post("/api/auth/roles/temporal/desactivar/", {}, format="json")
    assert en_uso.status_code == 400 and "1 persona" in en_uso.json()["detail"]
    rol.asignaciones.all().delete()
    assert (
        api.post("/api/auth/roles/temporal/desactivar/", {}, format="json").json()["activo"]
        is False
    )
    assert "temporal" not in [r["clave"] for r in api.get("/api/auth/roles/").json()]
    assert "temporal" in [r["clave"] for r in api.get("/api/auth/roles/?todos=1").json()]
    assert api.post("/api/auth/roles/temporal/activar/", {}, format="json").json()["activo"] is True


def test_solo_quien_administra_roles_los_crea_o_edita(db):
    anciano = cliente(usuario("55 0000 0027", "anciano"))
    nuevo = {"nombre": "X", "nivel": 5, "permisos": []}
    assert anciano.post("/api/auth/roles/", nuevo, format="json").status_code == 403
    assert (
        anciano.patch("/api/auth/roles/lider/", {"nombre": "Y"}, format="json").status_code == 403
    )


def test_vista_de_lo_que_puede_hacer_una_persona(db):
    api = cliente(_secretaria())
    lider = usuario("55 0000 0028", "lider")
    filas = api.get(f"/api/auth/users/{lider.pk}/permisos/").json()
    acciones = {a["codigo"]: a["roles"] for f in filas for a in f["acciones"]}
    assert acciones == {
        "personas.crear": ["Líder / Maestro"],
        "usuarios.invitar": ["Líder / Maestro"],
    }
    assert api.get("/api/auth/permisos/").json()[0]["modulo"] == "Personas"


def test_la_secretaria_no_asigna_super_usuario_pero_si_secretaria_y_pastor(db):
    otro = usuario("55 0000 0029")
    api = cliente(_secretaria())
    url = f"/api/auth/users/{otro.pk}/roles/"
    r = api.post(url, {"roles": ["admin_tecnico"]}, format="json")
    assert r.status_code == 403 and r.json()["code"] == "role_not_allowed"
    assert api.post(url, {"roles": ["secretaria"]}, format="json").status_code == 200
    assert api.post(url, {"roles": ["pastor"]}, format="json").status_code == 200
