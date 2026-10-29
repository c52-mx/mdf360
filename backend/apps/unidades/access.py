"""Alcance por unidad: quien es encargado, respaldo o servidor de una unidad ve solo esa unidad.

Los roles de una persona en cada unidad (y en cada grupo) son independientes: ser encargado de
la cafetería no da ningún acceso a un grupo, ni al revés.
"""

from apps.accounts.permissions import tiene_permiso

from .models import Unidad, UnidadMiembro

R = UnidadMiembro.Rol
GESTORES = {R.ENCARGADO, R.RESPALDO}


def roles_en(user, unidad: Unidad) -> set[str]:
    persona = getattr(user, "persona", None)
    if persona is None:
        return set()
    return set(
        UnidadMiembro.objects.filter(unidad=unidad, persona=persona, activo=True).values_list(
            "rol", flat=True
        )
    )


def unidades_visibles(user):
    if tiene_permiso(user, "unidades.ver_todas"):
        return Unidad.objects.all()
    persona = getattr(user, "persona", None)
    if persona is None:
        return Unidad.objects.none()
    ids = UnidadMiembro.objects.filter(persona=persona, activo=True).values_list(
        "unidad_id", flat=True
    )
    return Unidad.objects.filter(pk__in=ids)


def puede_administrar(user) -> bool:
    return tiene_permiso(user, "unidades.gestionar")


def puede_ver(user, unidad: Unidad) -> bool:
    return unidades_visibles(user).filter(pk=unidad.pk).exists()


def puede_gestionar_integrantes(user, unidad: Unidad) -> bool:
    return puede_administrar(user) or bool(roles_en(user, unidad) & GESTORES)


def puede_publicar(user, unidad: Unidad) -> bool:
    return puede_gestionar_integrantes(user, unidad)
