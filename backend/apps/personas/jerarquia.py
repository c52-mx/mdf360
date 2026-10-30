"""Quién puede dar de baja, trasladar o reactivar a quién.

Solo quien tiene el permiso `personas.baja` (se concede a los roles desde la pantalla de roles),
está por encima de la persona en el organigrama y la tiene dentro de su alcance: nadie se da de
baja a sí mismo ni a alguien de su mismo nivel o superior. Una persona sin cuenta (sin roles)
cuenta como el nivel más bajo.

Alcance: quien ve todos los grupos (Pastor, Anciano…) alcanza a cualquier persona; los demás,
solo a la gente de los grupos donde su rol administra a los integrantes o consulta el historial
(Líder, Supervisor…).
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


def en_su_alcance(actor, persona) -> bool:
    if tiene_permiso(actor, "grupos.ver_todos") or tiene_permiso(actor, "grupos.gestionar"):
        return True
    from apps.accounts import equipos
    from apps.grupos.models import GrupoMiembro

    propia = getattr(actor, "persona", None)
    if propia is None:
        return False
    roles = equipos.con_permiso("grupo", "integrantes") | equipos.con_permiso("grupo", "historial")
    mis_grupos = GrupoMiembro.objects.filter(persona=propia, activo=True, rol__in=roles).values(
        "grupo_id"
    )
    return GrupoMiembro.objects.filter(
        persona=persona, activo=True, grupo_id__in=mis_grupos
    ).exists()


def puede_dar_baja(actor, persona) -> bool:
    if not tiene_permiso(actor, "personas.baja"):
        return False
    if persona.usuario_id is not None and persona.usuario_id == actor.pk:
        return False
    return nivel_de(actor) < nivel_de(persona.usuario) and en_su_alcance(actor, persona)
