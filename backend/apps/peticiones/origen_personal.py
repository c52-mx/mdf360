"""Las peticiones personales como origen: cualquier persona con sesión pide oración.

El origen es la propia cuenta (el id es el de su usuario). La ve quien la registró y quien ve
las peticiones de todos los orígenes (Pastor y Anciano). Con alcance «equipo de oración» la lee
además el equipo de oración.
"""

from apps.accounts.permissions import tiene_permiso

from . import registry


def _etiqueta(origen_id: int, referencia_id: int | None) -> str | None:
    return "Petición personal" if referencia_id is None else None


def _puede_registrar(user, origen_id: int) -> bool:
    return bool(getattr(user, "pk", None)) and origen_id == user.pk


def _acceso(user, origen_id: int) -> str | None:
    if tiene_permiso(user, "peticiones.ver_todas") or origen_id == getattr(user, "pk", None):
        return registry.LIDER
    return None


def _ids_por_acceso(user) -> dict[str, list[int] | None]:
    if tiene_permiso(user, "peticiones.ver_todas"):
        return {registry.LIDER: None, registry.MIEMBRO: []}
    return {registry.LIDER: [user.pk], registry.MIEMBRO: []}


def registrar_origen():
    registry.registrar(
        registry.Origen(
            tipo="persona",
            nombre="Petición personal",
            etiqueta=_etiqueta,
            puede_registrar=_puede_registrar,
            acceso=_acceso,
            ids_por_acceso=_ids_por_acceso,
        )
    )
