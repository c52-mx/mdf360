"""Alcance por ministerio: quien tiene un rol en un ministerio ve solo ese ministerio.

Los roles de una persona en cada ministerio (y en cada grupo) son independientes: ser encargado de
la cafetería no da ningún acceso a un grupo, ni al revés. Lo que permite cada rol lo configura
la administración en la pantalla de roles (RolEquipo, ámbito «ministerio»).
"""

from apps.accounts import equipos
from apps.accounts.permissions import tiene_permiso

from .models import Unidad, UnidadMiembro

AMBITO = "ministerio"


def roles_en(user, unidad: Unidad) -> set[str]:
    persona = getattr(user, "persona", None)
    if persona is None:
        return set()
    return set(
        UnidadMiembro.objects.filter(unidad=unidad, persona=persona, activo=True).values_list(
            "rol", flat=True
        )
    )


def permisos_en(user, unidad: Unidad) -> set[str]:
    """Lo que sus roles en ese ministerio le permiten."""
    return equipos.permisos_de_roles(AMBITO, roles_en(user, unidad))


def ids_con_rol_que_ve(user) -> list[int]:
    persona = getattr(user, "persona", None)
    if persona is None:
        return []
    return list(
        UnidadMiembro.objects.filter(
            persona=persona, activo=True, rol__in=equipos.con_permiso(AMBITO, "ver")
        )
        .values_list("unidad_id", flat=True)
        .distinct()
    )


def unidades_visibles(user):
    if tiene_permiso(user, "unidades.ver_todas"):
        return Unidad.objects.all()
    return Unidad.objects.filter(pk__in=ids_con_rol_que_ve(user))


def puede_administrar(user) -> bool:
    return tiene_permiso(user, "unidades.gestionar")


def puede_ver(user, unidad: Unidad) -> bool:
    return unidades_visibles(user).filter(pk=unidad.pk).exists()


def puede_gestionar_integrantes(user, unidad: Unidad) -> bool:
    return puede_administrar(user) or "integrantes" in permisos_en(user, unidad)


def puede_publicar(user, unidad: Unidad) -> bool:
    return puede_administrar(user) or "avisos" in permisos_en(user, unidad)
