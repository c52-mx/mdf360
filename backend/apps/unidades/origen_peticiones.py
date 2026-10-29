"""Los ministerios como origen de peticiones de oración.

Registra quien tenga el permiso «peticiones_registrar» en su rol del ministerio (y la
administración de ministerios). Ve todas las del ministerio quien tenga «peticiones_ver»; quien
solo sirve en el ministerio ve las que se compartieron con todo el ministerio.
"""

from apps.accounts import equipos
from apps.accounts.permissions import tiene_permiso
from apps.peticiones import registry

from . import access
from .models import Unidad, UnidadMiembro


def _etiqueta(unidad_id: int, referencia_id: int | None) -> str | None:
    if referencia_id is not None:
        return None  # un ministerio no tiene reuniones a las que referirse
    unidad = Unidad.objects.filter(pk=unidad_id, activa=True).first()
    return f"Ministerio · {unidad.nombre}" if unidad else None


def _puede_registrar(user, unidad_id: int) -> bool:
    unidad = Unidad.objects.filter(pk=unidad_id).first()
    if unidad is None:
        return False
    return access.puede_administrar(user) or "peticiones_registrar" in access.permisos_en(
        user, unidad
    )


def _acceso(user, unidad_id: int) -> str | None:
    if tiene_permiso(user, "peticiones.ver_todas"):
        return registry.LIDER
    unidad = Unidad.objects.filter(pk=unidad_id).first()
    if unidad is None:
        return None
    permisos = access.permisos_en(user, unidad)
    if "peticiones_ver" in permisos:
        return registry.LIDER
    return registry.MIEMBRO if "ver" in permisos else None


def _ids_por_acceso(user) -> dict[str, list[int] | None]:
    if tiene_permiso(user, "peticiones.ver_todas"):
        return {registry.LIDER: None, registry.MIEMBRO: []}
    persona = getattr(user, "persona", None)
    if persona is None:
        return {registry.LIDER: [], registry.MIEMBRO: []}
    membresias = UnidadMiembro.objects.filter(persona=persona, activo=True)
    return {
        registry.LIDER: list(
            membresias.filter(rol__in=equipos.con_permiso(access.AMBITO, "peticiones_ver"))
            .values_list("unidad_id", flat=True)
            .distinct()
        ),
        registry.MIEMBRO: list(
            membresias.filter(rol__in=equipos.con_permiso(access.AMBITO, "ver"))
            .values_list("unidad_id", flat=True)
            .distinct()
        ),
    }


def registrar_origen():
    registry.registrar(
        registry.Origen(
            tipo="unidad",
            nombre="Ministerio",
            etiqueta=_etiqueta,
            puede_registrar=_puede_registrar,
            acceso=_acceso,
            ids_por_acceso=_ids_por_acceso,
        )
    )
