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
    assert Rol.objects.count() == 9
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
