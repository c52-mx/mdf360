"""Los Grupos de Conexión como origen de peticiones de oración.

Registran el Líder y el Secretario (y el Pastor). Quién lee depende del alcance que se eligió al
registrar: «solo líderes» (Líder, Supervisor, Pastor y Anciano), «mi grupo» (todos los
integrantes del grupo) o «equipo de oración» (además, quien tenga ese rol).
"""

from apps.accounts.permissions import tiene_permiso
from apps.peticiones import registry

from .access import roles_en
from .models import Grupo, GrupoMiembro, Reunion

R = GrupoMiembro.Rol


def _etiqueta(grupo_id: int, referencia_id: int | None) -> str | None:
    grupo = Grupo.objects.filter(pk=grupo_id, activo=True).first()
    if grupo is None:
        return None
    etiqueta = f"Grupo de Conexión · {grupo.nombre}"
    if referencia_id is not None:
        reunion = Reunion.objects.filter(pk=referencia_id, grupo=grupo).first()
        if reunion is None:
            return None  # la reunión no pertenece a ese grupo
        etiqueta += f" · reunión del {reunion.fecha.strftime('%d/%m/%Y')}"
    return etiqueta


def _puede_registrar(user, grupo_id: int) -> bool:
    grupo = Grupo.objects.filter(pk=grupo_id).first()
    if grupo is None:
        return False
    return tiene_permiso(user, "grupos.gestionar") or bool(
        roles_en(user, grupo) & {R.LIDER, R.SECRETARIO}
    )


def _acceso(user, grupo_id: int) -> str | None:
    """LIDER: Pastor, Anciano, Líder o Supervisor. MIEMBRO: cualquier integrante activo."""
    if tiene_permiso(user, "peticiones.ver_todas"):
        return registry.LIDER
    grupo = Grupo.objects.filter(pk=grupo_id).first()
    if grupo is None:
        return None
    roles = roles_en(user, grupo)
    if roles & {R.LIDER, R.SUPERVISOR}:
        return registry.LIDER
    return registry.MIEMBRO if roles else None


def _ids_por_acceso(user) -> dict[str, list[int] | None]:
    if tiene_permiso(user, "peticiones.ver_todas"):
        return {registry.LIDER: None, registry.MIEMBRO: []}
    persona = getattr(user, "persona", None)
    if persona is None:
        return {registry.LIDER: [], registry.MIEMBRO: []}
    membresias = GrupoMiembro.objects.filter(persona=persona, activo=True)
    return {
        registry.LIDER: list(
            membresias.filter(rol__in=[R.LIDER, R.SUPERVISOR]).values_list("grupo_id", flat=True)
        ),
        registry.MIEMBRO: list(membresias.values_list("grupo_id", flat=True).distinct()),
    }


def registrar_origen():
    registry.registrar(
        registry.Origen(
            tipo="grupo",
            nombre="Grupo de Conexión",
            etiqueta=_etiqueta,
            puede_registrar=_puede_registrar,
            acceso=_acceso,
            ids_por_acceso=_ids_por_acceso,
        )
    )
