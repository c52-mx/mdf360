"""Dashboard de supervisión (M3-07): salud y avance de los grupos que la persona puede consultar.

Respeta la matriz de confidencialidad: solo entran los grupos cuyo historial puede ver (el
Secretario no), las ofrendas solo si puede ver finanzas del grupo, y las peticiones solo las que
puede leer.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.core import config
from apps.peticiones import services as peticiones

from . import access
from .models import Asistencia, GrupoMiembro, Reunion
from .ofrendas import Ofrenda, puede_ver_finanzas_grupo

SEMANAS = 8


def _lunes(dia: date) -> date:
    return dia - timedelta(days=dia.weekday())


def _pct(presentes: int, registrados: int) -> int | None:
    return round(100 * presentes / registrados) if registrados else None


def _totales_por_reunion(reuniones):
    """{reunion_id: (presentes, registrados)} en una sola consulta."""
    filas = (
        Asistencia.objects.filter(reunion__in=reuniones)
        .values("reunion_id")
        .annotate(registrados=Count("id"), presentes=Count("id", filter=Q(presente=True)))
    )
    return {f["reunion_id"]: (f["presentes"], f["registrados"]) for f in filas}


def _grupo(user, grupo, hoy: date, visibles_peticiones) -> dict:
    desde = hoy - timedelta(weeks=SEMANAS)
    reuniones = list(grupo.reuniones.filter(fecha__gte=desde).order_by("-fecha"))
    totales = _totales_por_reunion(reuniones)
    con_lista = [(r, totales[r.pk]) for r in reuniones if r.pk in totales]
    recientes = con_lista[:4]
    presentes = sum(t[0] for _, t in recientes)
    registrados = sum(t[1] for _, t in recientes)
    asistencia = _pct(presentes, registrados)

    inicio_semana = _lunes(hoy)
    lista_semana = any(r.fecha >= inicio_semana for r, _ in con_lista)
    # «Pendiente» solo si ya llegó (o pasó) el día de reunión de esta semana
    ya_toca = grupo.dia_semana is not None and hoy.weekday() >= grupo.dia_semana
    sin_lista = ya_toca and not lista_semana

    integrantes = (
        GrupoMiembro.objects.filter(grupo=grupo, activo=True)
        .values("persona_id")
        .distinct()
        .count()
    )
    datos = {
        "id": grupo.pk,
        "nombre": grupo.nombre,
        "tipo": grupo.tipo,
        "dia": grupo.dia_semana,
        "integrantes": integrantes,
        "reuniones_8_semanas": len(con_lista),
        "asistencia_pct": asistencia,
        "ultimas": [
            {"fecha": r.fecha.isoformat(), "presentes": t[0], "registrados": t[1]}
            for r, t in reversed(con_lista[:8])
        ],
        "ultima_reunion": reuniones[0].fecha.isoformat() if reuniones else None,
        "sin_lista_esta_semana": bool(sin_lista),
        "ofrendas": None,
        "peticiones_activas": None,
    }
    if puede_ver_finanzas_grupo(user, grupo):
        hace_30 = hoy - timedelta(days=30)
        of = Ofrenda.objects.filter(reunion__grupo=grupo)
        datos["ofrendas"] = {
            "avalado_30_dias": str(
                of.filter(estado="avalada", reunion__fecha__gte=hace_30).aggregate(t=Sum("monto"))[
                    "t"
                ]
                or Decimal("0")
            ),
            "pendientes": of.filter(estado="pendiente").count(),
            "con_diferencia": of.filter(estado="diferencia").count(),
        }
    if visibles_peticiones is not None:
        datos["peticiones_activas"] = visibles_peticiones.filter(
            origen_tipo="grupo", origen_id=grupo.pk, estado="activa"
        ).count()
    return datos


def construir(user) -> dict:
    hoy = timezone.localdate()
    grupos = [
        g
        for g in access.grupos_visibles(user).filter(activo=True)
        if access.puede_ver_historial(user, g)
    ]
    visibles_peticiones = peticiones.peticiones_visibles(user)
    tarjetas = [_grupo(user, g, hoy, visibles_peticiones) for g in grupos]

    # Serie semanal agregada de todos los grupos consultados
    inicio = _lunes(hoy) - timedelta(weeks=SEMANAS - 1)
    ids = [g.pk for g in grupos]
    reuniones = list(Reunion.objects.filter(grupo_id__in=ids, fecha__gte=inicio))
    totales = _totales_por_reunion(reuniones)
    semanas = {inicio + timedelta(weeks=i): [0, 0] for i in range(SEMANAS)}
    for r in reuniones:
        if r.pk in totales:
            sem = semanas[_lunes(r.fecha)]
            sem[0] += totales[r.pk][0]
            sem[1] += totales[r.pk][1]
    serie = [
        {"semana": s.isoformat(), "presentes": p, "registrados": n, "pct": _pct(p, n)}
        for s, (p, n) in semanas.items()
    ]

    minimo = int(config.obtener("grupos.asistencia_minima_pct"))
    alertas = []
    for t in tarjetas:
        if t["sin_lista_esta_semana"]:
            alertas.append({"tipo": "sin_lista", "grupo_id": t["id"], "grupo": t["nombre"]})
        if t["asistencia_pct"] is not None and t["asistencia_pct"] < minimo:
            alertas.append(
                {"tipo": "asistencia_baja", "grupo_id": t["id"], "grupo": t["nombre"],
                 "valor": t["asistencia_pct"]}
            )  # fmt: skip
        if t["ofrendas"] and t["ofrendas"]["con_diferencia"]:
            alertas.append(
                {"tipo": "ofrenda_con_diferencia", "grupo_id": t["id"], "grupo": t["nombre"],
                 "valor": t["ofrendas"]["con_diferencia"]}
            )  # fmt: skip

    presentes = sum(s["presentes"] for s in serie[-4:])
    registrados = sum(s["registrados"] for s in serie[-4:])
    return {
        "resumen": {
            "grupos": len(tarjetas),
            "integrantes": sum(t["integrantes"] for t in tarjetas),
            "asistencia_pct": _pct(presentes, registrados),
            "alertas": len(alertas),
            "asistencia_minima_pct": minimo,
        },
        "serie": serie,
        "grupos": tarjetas,
        "alertas": alertas,
    }
