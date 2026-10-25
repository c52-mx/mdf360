"""Alcance por grupo (M1-08): qué puede hacer cada persona según su rol dentro del grupo.

Sigue la matriz de confidencialidad aprobada (v3.2, sec. 3.3):
- Pastor y Anciano ven todos los grupos; el Pastor además los administra.
- Supervisor: consulta sus grupos. Líder: consulta y modifica la asistencia de su grupo.
- Secretario: captura la asistencia y la corrige el mismo día; no consulta el historial.
- Tesorero y Anfitrión no acceden a la asistencia.
"""

from datetime import date

from apps.accounts.permissions import tiene_permiso

from .models import Grupo, GrupoMiembro, Reunion

R = GrupoMiembro.Rol


def roles_en(user, grupo: Grupo) -> set[str]:
    persona = getattr(user, "persona", None)
    if persona is None:
        return set()
    return set(
        GrupoMiembro.objects.filter(grupo=grupo, persona=persona, activo=True).values_list(
            "rol", flat=True
        )
    )


def grupos_visibles(user):
    if tiene_permiso(user, "grupos.ver_todos"):
        return Grupo.objects.all()
    persona = getattr(user, "persona", None)
    if persona is None:
        return Grupo.objects.none()
    ids = GrupoMiembro.objects.filter(
        persona=persona, activo=True, rol__in=[R.SUPERVISOR, R.LIDER, R.SECRETARIO]
    ).values_list("grupo_id", flat=True)
    return Grupo.objects.filter(pk__in=ids)


def puede_administrar(user) -> bool:
    return tiene_permiso(user, "grupos.gestionar")


def puede_ver_grupo(user, grupo: Grupo) -> bool:
    return grupos_visibles(user).filter(pk=grupo.pk).exists()


def puede_gestionar_integrantes(user, grupo: Grupo) -> bool:
    return puede_administrar(user) or R.LIDER in roles_en(user, grupo)


def puede_ver_historial(user, grupo: Grupo) -> bool:
    if tiene_permiso(user, "grupos.ver_todos"):
        return True
    return bool(roles_en(user, grupo) & {R.SUPERVISOR, R.LIDER})


def puede_capturar(user, grupo: Grupo) -> bool:
    return puede_administrar(user) or bool(roles_en(user, grupo) & {R.LIDER, R.SECRETARIO})


def puede_modificar_asistencia(user, reunion: Reunion) -> bool:
    """Líder y Pastor siempre; Secretario solo el mismo día de la reunión."""
    if puede_administrar(user) or R.LIDER in roles_en(user, reunion.grupo):
        return True
    return R.SECRETARIO in roles_en(user, reunion.grupo) and reunion.fecha == date.today()


def puede_ver_reunion(user, reunion: Reunion) -> bool:
    if puede_ver_historial(user, reunion.grupo):
        return True
    return R.SECRETARIO in roles_en(user, reunion.grupo) and reunion.fecha == date.today()


def puede_ver_estudios(user) -> bool:
    if tiene_permiso(user, "grupos.material") or tiene_permiso(user, "grupos.ver_todos"):
        return True
    persona = getattr(user, "persona", None)
    return bool(
        persona
        and GrupoMiembro.objects.filter(
            persona=persona, activo=True, rol__in=[R.SUPERVISOR, R.LIDER, R.SECRETARIO]
        ).exists()
    )
