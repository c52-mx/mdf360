"""Los Grupos de Conexión como origen del tablero de mensajes.

Publican los roles que tengan ese permiso (Líder, Supervisor, Secretario…) y la
administración. Leen todos los integrantes activos del grupo y quienes ven todos los grupos
(Pastor y Anciano).
"""

from apps.accounts.permissions import tiene_permiso
from apps.tablero import registry

from .access import permisos_en, roles_en
from .models import Grupo, GrupoMiembro


def _grupo(grupo_id: int):
    return Grupo.objects.filter(pk=grupo_id, activo=True).first()


def _etiqueta(grupo_id: int) -> str | None:
    grupo = _grupo(grupo_id)
    return f"Grupo de Conexión · {grupo.nombre}" if grupo else None


def _puede_publicar(user, grupo_id: int) -> bool:
    grupo = _grupo(grupo_id)
    if grupo is None:
        return False
    if tiene_permiso(user, "grupos.gestionar"):
        return True
    return "avisos" in permisos_en(user, grupo)


def _puede_moderar(user, grupo_id: int) -> bool:
    """Fijar o quitar avisos ajenos. Publicar no basta: un Asistente publica pero no modera."""
    grupo = _grupo(grupo_id)
    if grupo is None:
        return False
    if tiene_permiso(user, "grupos.gestionar"):
        return True
    return "avisos_moderar" in permisos_en(user, grupo)


def _puede_leer(user, grupo_id: int) -> bool:
    grupo = _grupo(grupo_id)
    if grupo is None:
        return False
    return tiene_permiso(user, "grupos.ver_todos") or bool(roles_en(user, grupo))


def _ids_legibles(user) -> list[int] | None:
    if tiene_permiso(user, "grupos.ver_todos"):
        return None
    persona = getattr(user, "persona", None)
    if persona is None:
        return []
    return list(
        GrupoMiembro.objects.filter(persona=persona, activo=True)
        .values_list("grupo_id", flat=True)
        .distinct()
    )


def _listar(user) -> list[tuple[int, str]]:
    ids = _ids_legibles(user)
    grupos = Grupo.objects.filter(activo=True)
    if ids is not None:
        grupos = grupos.filter(pk__in=ids)
    return [(g.pk, f"Grupo de Conexión · {g.nombre}") for g in grupos.order_by("nombre")]


def registrar_origen():
    registry.registrar(
        registry.Origen(
            tipo="grupo",
            nombre="Grupo de Conexión",
            etiqueta=_etiqueta,
            puede_publicar=_puede_publicar,
            puede_moderar=_puede_moderar,
            puede_leer=_puede_leer,
            ids_legibles=_ids_legibles,
            listar=_listar,
            ruta=lambda grupo_id: f"/grupos/{grupo_id}",
        )
    )
