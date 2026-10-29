"""Bienes ligados: cada persona registra y mantiene sus vehículos."""

from apps.accounts.models import AsignacionRol, Rol, User
from apps.core.models import AuditEvent

from .models import Vehiculo
from .test_perfil import PIN, api_de, yo  # noqa: F401

URL = "/api/personas/mi-perfil/vehiculos/"


def test_registra_corrige_y_quita_sus_vehiculos(yo):  # noqa: F811
    r = api_de(yo).post(
        URL,
        {"tipo": "auto", "marca": "Nissan", "modelo": "Versa", "anio": 2020, "placas": "abc 123-d"},
        format="json",
    )
    assert r.status_code == 201 and r.json()["placas"] == "ABC123-D"
    pk = r.json()["id"]
    api_de(yo).post(URL, {"tipo": "moto", "color": "Negra"}, format="json")
    assert len(api_de(yo).get(URL).json()) == 2
    cambio = api_de(yo).patch(f"{URL}{pk}/", {"color": "Gris"}, format="json")
    assert cambio.status_code == 200 and cambio.json()["color"] == "Gris"
    assert api_de(yo).delete(f"{URL}{pk}/").status_code == 204
    assert Vehiculo.objects.filter(persona=yo.persona).count() == 1
    acciones = set(AuditEvent.objects.values_list("action", flat=True))
    assert {
        "persona.vehiculo_agregado",
        "persona.vehiculo_editado",
        "persona.vehiculo_quitado",
    } <= acciones


def test_nadie_toca_los_vehiculos_de_otra_persona(yo):  # noqa: F811
    otro = User.objects.create_user("55 0000 0102", pin=PIN, nombre="Otro")
    AsignacionRol.objects.create(usuario=otro, rol=Rol.objects.get(clave="miembro"))
    ajeno = api_de(otro).post(URL, {"tipo": "auto"}, format="json").json()["id"]
    assert api_de(yo).patch(f"{URL}{ajeno}/", {"color": "Rojo"}, format="json").status_code == 404
    assert api_de(yo).delete(f"{URL}{ajeno}/").status_code == 404
    assert api_de(yo).get(URL).json() == []


def test_el_tipo_debe_ser_valido(yo):  # noqa: F811
    assert api_de(yo).post(URL, {"tipo": "cohete"}, format="json").status_code == 400
