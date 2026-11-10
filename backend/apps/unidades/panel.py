"""Panel de un ministerio para los roles superiores.

Solo cuenta lo que ya existe: la gente del equipo y cómo creció, las publicaciones del muro y las
peticiones del ministerio (solo cuántas, nunca su contenido, que va cifrado). Inventario, gastos y
agenda siguen en definición y no aparecen aquí.
"""

from collections import Counter
from datetime import date, timedelta

from django.utils import timezone

from apps.accounts import equipos
from apps.accounts.permissions import tiene_permiso
from apps.muro.models import Publicacion
from apps.peticiones.models import Peticion

from . import access
from .models import Unidad, UnidadMiembro

MESES = 6


def puede_ver_panel(user, unidad: Unidad) -> bool:
    """Administración de ministerios, quien ve todos y los roles que gestionan a la gente."""
    return (
        access.puede_administrar(user)
        or tiene_permiso(user, "unidades.ver_todas")
        or "integrantes" in access.permisos_en(user, unidad)
    )


def _ultimos_meses(hoy: date, cuantos: int) -> list[str]:
    """Claves AAAA-MM de los últimos meses, del más antiguo al actual."""
    claves = []
    año, mes = hoy.year, hoy.month
    for _ in range(cuantos):
        claves.append(f"{año:04d}-{mes:02d}")
        mes -= 1
        if mes == 0:
            año, mes = año - 1, 12
    return claves[::-1]


def resumen(unidad: Unidad) -> dict:
    hoy = timezone.localdate()
    meses = _ultimos_meses(hoy, MESES)
    miembros = UnidadMiembro.objects.filter(unidad=unidad)
    activos = miembros.filter(activo=True)
    nombres = equipos.nombres("ministerio")

    por_rol = Counter(activos.values_list("rol", flat=True))
    personas_activas = activos.values("persona_id").distinct().count()

    # Se cuenta una vez a cada persona, en el mes en que empezó a servir en el ministerio
    primera = {}
    for persona_id, desde in miembros.values_list("persona_id", "desde"):
        if persona_id not in primera or desde < primera[persona_id]:
            primera[persona_id] = desde
    sumaron = Counter(f"{d.year:04d}-{d.month:02d}" for d in primera.values())

    desde_mensajes = date.fromisoformat(f"{meses[0]}-01")
    del_ministerio = Publicacion.objects.filter(
        audiencias__tipo="unidad", audiencias__ref_id=unidad.pk, eliminada=False
    )
    mensajes = Counter(
        f"{m.year:04d}-{m.month:02d}"
        for m in del_ministerio.filter(creada_en__date__gte=desde_mensajes).values_list(
            "creada_en", flat=True
        )
    )
    ultimo = del_ministerio.order_by("-creada_en").values_list("creada_en", flat=True).first()

    peticiones = Counter(
        Peticion.objects.filter(origen_tipo="unidad", origen_id=unidad.pk).values_list(
            "estado", flat=True
        )
    )
    nuevos_30 = sum(1 for d in primera.values() if d >= hoy - timedelta(days=30))

    return {
        "integrantes": personas_activas,
        "nuevos_30_dias": nuevos_30,
        "salieron": miembros.filter(activo=False).values("persona_id").distinct().count(),
        "por_rol": [
            {"rol": clave, "rol_display": nombres.get(clave, clave), "total": total}
            for clave, total in sorted(por_rol.items(), key=lambda x: (-x[1], x[0]))
        ],
        "meses": [
            {"mes": mes, "sumaron": sumaron.get(mes, 0), "mensajes": mensajes.get(mes, 0)}
            for mes in meses
        ],
        "ultimo_mensaje": ultimo.isoformat() if ultimo else None,
        "peticiones": {
            "activas": peticiones.get(Peticion.Estado.ACTIVA, 0),
            "atendidas": peticiones.get(Peticion.Estado.ATENDIDA, 0),
        },
    }
