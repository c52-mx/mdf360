"""Las Unidades como origen del tablero de mensajes.

Publican el encargado, el respaldo y la administración de unidades. Leen todos los integrantes
activos de la unidad y quienes ven todas las unidades.
"""

from apps.accounts.permissions import tiene_permiso
from apps.tablero import registry

from . import access
from .models import Unidad, UnidadMiembro


def _unidad(unidad_id: int):
    return Unidad.objects.filter(pk=unidad_id, activa=True).first()


def _etiqueta(unidad_id: int) -> str | None:
    unidad = _unidad(unidad_id)
    return f"Unidad · {unidad.nombre}" if unidad else None


def _puede_publicar(user, unidad_id: int) -> bool:
    unidad = _unidad(unidad_id)
    return unidad is not None and access.puede_publicar(user, unidad)


def _puede_leer(user, unidad_id: int) -> bool:
    unidad = _unidad(unidad_id)
    if unidad is None:
        return False
    return tiene_permiso(user, "unidades.ver_todas") or bool(access.roles_en(user, unidad))


def _ids_legibles(user) -> list[int] | None:
    if tiene_permiso(user, "unidades.ver_todas"):
        return None
    persona = getattr(user, "persona", None)
    if persona is None:
        return []
    return list(
        UnidadMiembro.objects.filter(persona=persona, activo=True)
        .values_list("unidad_id", flat=True)
        .distinct()
    )


def _listar(user) -> list[tuple[int, str]]:
    ids = _ids_legibles(user)
    unidades = Unidad.objects.filter(activa=True)
    if ids is not None:
        unidades = unidades.filter(pk__in=ids)
    return [(u.pk, f"Unidad · {u.nombre}") for u in unidades.order_by("nombre")]


def registrar_origen():
    registry.registrar(
        registry.Origen(
            tipo="unidad",
            nombre="Unidad",
            etiqueta=_etiqueta,
            puede_publicar=_puede_publicar,
            puede_leer=_puede_leer,
            ids_legibles=_ids_legibles,
            listar=_listar,
            ruta=lambda unidad_id: f"/unidades/{unidad_id}",
        )
    )
