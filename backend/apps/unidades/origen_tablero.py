"""Los ministerios como origen del tablero de mensajes.

Publican los roles con ese permiso (encargado, respaldo…) y la administración de ministerios.
Leen quienes tienen un rol que ve el ministerio y quienes ven todos los ministerios.
"""

from apps.accounts.permissions import tiene_permiso
from apps.tablero import registry

from . import access
from .models import Unidad


def _unidad(unidad_id: int):
    return Unidad.objects.filter(pk=unidad_id, activa=True).first()


def _etiqueta(unidad_id: int) -> str | None:
    unidad = _unidad(unidad_id)
    return f"Ministerio · {unidad.nombre}" if unidad else None


def _puede_publicar(user, unidad_id: int) -> bool:
    unidad = _unidad(unidad_id)
    return unidad is not None and access.puede_publicar(user, unidad)


def _puede_leer(user, unidad_id: int) -> bool:
    unidad = _unidad(unidad_id)
    if unidad is None:
        return False
    return access.puede_ver(user, unidad)


def _ids_legibles(user) -> list[int] | None:
    if tiene_permiso(user, "unidades.ver_todas"):
        return None
    return access.ids_con_rol_que_ve(user)


def _listar(user) -> list[tuple[int, str]]:
    ids = _ids_legibles(user)
    unidades = Unidad.objects.filter(activa=True)
    if ids is not None:
        unidades = unidades.filter(pk__in=ids)
    return [(u.pk, f"Ministerio · {u.nombre}") for u in unidades.order_by("nombre")]


def registrar_origen():
    registry.registrar(
        registry.Origen(
            tipo="unidad",
            nombre="Ministerio",
            etiqueta=_etiqueta,
            puede_publicar=_puede_publicar,
            puede_leer=_puede_leer,
            ids_legibles=_ids_legibles,
            listar=_listar,
            ruta=lambda unidad_id: f"/ministerios/{unidad_id}",
        )
    )
