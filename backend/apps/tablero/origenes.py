"""Orígenes del tablero que no pertenecen a un grupo ni a un ministerio.

- «iglesia»: un solo tablero con los avisos a toda la iglesia. Lo leen todas las personas con
  acceso y lo publica quien tiene el permiso `avisos.iglesia`.
- «persona»: los avisos dirigidos a una persona. Solo los lee ella (y quien administra personas
  no los ve: son para ella) y los publica quien tiene el permiso `avisos.personas`.
"""

from apps.accounts.permissions import tiene_permiso
from apps.personas.models import Persona

from . import registry
from .models import Mensaje

ID_IGLESIA = 1


def _persona_de(user):
    return getattr(user, "persona", None)


# ---------- toda la iglesia ----------
def _etiqueta_iglesia(origen_id: int) -> str | None:
    return "Aviso general · Toda la iglesia" if origen_id == ID_IGLESIA else None


def _leer_iglesia(user, origen_id: int) -> bool:
    return origen_id == ID_IGLESIA and bool(user and user.is_authenticated and user.is_active)


def _publicar_iglesia(user, origen_id: int) -> bool:
    return origen_id == ID_IGLESIA and tiene_permiso(user, "avisos.iglesia")


# ---------- una persona ----------
def _etiqueta_persona(persona_id: int) -> str | None:
    persona = Persona.objects.filter(pk=persona_id, activo=True).first()
    return f"Aviso personal · {persona.nombre_completo}" if persona else None


def _leer_persona(user, persona_id: int) -> bool:
    propia = _persona_de(user)
    return propia is not None and propia.pk == persona_id


def _publicar_persona(user, persona_id: int) -> bool:
    return (
        tiene_permiso(user, "avisos.personas")
        and Persona.objects.filter(pk=persona_id, activo=True).exists()
    )


def _ids_persona(user) -> list[int] | None:
    propia = _persona_de(user)
    return [propia.pk] if propia is not None else []


def _listar_persona(user) -> list[tuple[int, str]]:
    """Solo aparece en «Avisos» cuando ya le escribieron algo."""
    propia = _persona_de(user)
    if propia is None:
        return []
    hay = Mensaje.objects.filter(origen_tipo="persona", origen_id=propia.pk, eliminado=False)
    return [(propia.pk, "Avisos para ti")] if hay.exists() else []


def registrar_origenes():
    registry.registrar(
        registry.Origen(
            tipo="iglesia",
            nombre="Toda la iglesia",
            etiqueta=_etiqueta_iglesia,
            puede_publicar=_publicar_iglesia,
            puede_leer=_leer_iglesia,
            ids_legibles=lambda user: [ID_IGLESIA],
            listar=lambda user: [(ID_IGLESIA, "Toda la iglesia")],
        )
    )
    registry.registrar(
        registry.Origen(
            tipo="persona",
            nombre="Para ti",
            etiqueta=_etiqueta_persona,
            puede_publicar=_publicar_persona,
            puede_leer=_leer_persona,
            ids_legibles=_ids_persona,
            listar=_listar_persona,
        )
    )
