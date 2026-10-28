"""Quién puede dar de baja, trasladar o reactivar a quién.

Solo quien tiene el permiso `personas.baja` y está por encima de la persona en el organigrama:
nadie se da de baja a sí mismo ni a alguien de su mismo nivel o superior. Una persona sin cuenta
(sin roles) cuenta como el nivel más bajo.
"""

from apps.accounts.models import Rol
from apps.accounts.permissions import tiene_permiso

SIN_ROL = 99


def nivel_de(user) -> int:
    """Nivel jerárquico más alto (número más bajo) entre los roles activos de la cuenta."""
    if user is None:
        return SIN_ROL
    return min(
        Rol.objects.filter(asignaciones__usuario=user, activo=True).values_list("nivel", flat=True),
        default=SIN_ROL,
    )


def puede_dar_baja(actor, persona) -> bool:
    if not tiene_permiso(actor, "personas.baja"):
        return False
    if persona.usuario_id is not None and persona.usuario_id == actor.pk:
        return False
    return nivel_de(actor) < nivel_de(persona.usuario)
