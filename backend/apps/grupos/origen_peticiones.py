"""Los Grupos de Conexión como origen de peticiones de oración.

Reglas (matriz de confidencialidad aprobada): registran el Líder y el Secretario (y el Pastor);
ven solo el Líder de su grupo, el Supervisor de sus grupos, el Pastor y el Anciano.
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


def _puede_ver(user, grupo_id: int) -> bool:
    if tiene_permiso(user, "peticiones.ver_todas"):
        return True
    grupo = Grupo.objects.filter(pk=grupo_id).first()
    return grupo is not None and bool(roles_en(user, grupo) & {R.LIDER, R.SUPERVISOR})


def _ids_visibles(user) -> list[int] | None:
    if tiene_permiso(user, "peticiones.ver_todas"):
        return None
    persona = getattr(user, "persona", None)
    if persona is None:
        return []
    return list(
        GrupoMiembro.objects.filter(
            persona=persona, activo=True, rol__in=[R.LIDER, R.SUPERVISOR]
        ).values_list("grupo_id", flat=True)
    )


def registrar_origen():
    registry.registrar(
        registry.Origen(
            tipo="grupo",
            nombre="Grupo de Conexión",
            etiqueta=_etiqueta,
            puede_registrar=_puede_registrar,
            puede_ver=_puede_ver,
            ids_visibles=_ids_visibles,
        )
    )
