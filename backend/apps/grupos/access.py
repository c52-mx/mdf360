"""Alcance por grupo (M1-08): qué puede hacer cada persona según su rol dentro del grupo.

Sigue la matriz de confidencialidad aprobada (v3.2, sec. 3.3):
- Pastor y Anciano ven todos los grupos; el Pastor además los administra.
- Supervisor: consulta sus grupos. Líder: consulta y modifica la asistencia de su grupo.
- Secretario: captura la asistencia y la corrige el mismo día; no consulta el historial.
- Tesorero y Anfitrión no acceden a la asistencia.
"""

from datetime import date, datetime, timedelta

from django.utils import timezone

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


VENTANA_SINCRONIZACION = timedelta(days=7)


class CapturaInvalida(Exception):
    pass


def momento_captura(valor: datetime | None) -> datetime | None:
    """Momento en que se capturó sin conexión. Se acota para que no se pueda adelantar ni usar
    una captura demasiado antigua; devuelve None si no se envió."""
    if valor is None:
        return None
    ahora = timezone.now()
    if valor > ahora + timedelta(minutes=10):
        return ahora  # reloj del teléfono adelantado
    if valor < ahora - VENTANA_SINCRONIZACION:
        raise CapturaInvalida("La captura sin conexión es demasiado antigua para sincronizarse.")
    return valor


def dia_efectivo(momento: datetime | None) -> date:
    """Día contra el que se evalúa la regla «el Secretario solo captura el mismo día»."""
    if momento is None:
        return timezone.localdate()
    return timezone.localtime(momento).date()


def puede_modificar_asistencia(user, reunion: Reunion, dia: date | None = None) -> bool:
    """Líder y Pastor siempre; Secretario solo el mismo día de la reunión (el día en que
    capturó, si la captura se hizo sin conexión y se sincroniza después)."""
    if puede_administrar(user) or R.LIDER in roles_en(user, reunion.grupo):
        return True
    dia = dia or timezone.localdate()
    return R.SECRETARIO in roles_en(user, reunion.grupo) and reunion.fecha == dia


def puede_ver_reunion(user, reunion: Reunion, dia: date | None = None) -> bool:
    if puede_ver_historial(user, reunion.grupo):
        return True
    dia = dia or timezone.localdate()
    return R.SECRETARIO in roles_en(user, reunion.grupo) and reunion.fecha == dia


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
