"""Ofrendas de la iglesia, el catálogo de tipos y el resumen financiero.

Reglas (acordadas tras las pruebas):
- Capturan la Secretaria, el Pastor y la Tesorería (permiso ofrendas.iglesia_capturar) y todas
  pasan por aval con PIN de otra persona (ofrendas.iglesia_avalar): nadie avala lo que capturó.
- Nadie ve lo de los demás, salvo quien tiene ofrendas.ver_todas (Pastor, Secretaria, Super
  Usuario QA). Quien captura ve lo suyo; quien avala ve lo que está por avalar.
- Los tipos de ofrenda son un único catálogo: cada tipo dice si se usa en grupos, en la iglesia
  o en ambos.
"""

from collections import defaultdict
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.accounts.permissions import tiene_permiso
from apps.core import audit

from . import ofrendas as base
from .models import (
    Grupo,
    Ofrenda,
    OfrendaIglesia,
    OfrendaIglesiaMovimiento,
    OfrendaMovimiento,
    TipoOfrenda,
)

LIMITE_FILAS = 5000
CERO = Decimal("0")


# ---------- permisos ----------
def puede_capturar(user) -> bool:
    return tiene_permiso(user, "ofrendas.iglesia_capturar")


def puede_avalar(user, ofrenda: OfrendaIglesia | None = None) -> bool:
    if not tiene_permiso(user, "ofrendas.iglesia_avalar"):
        return False
    return ofrenda is None or ofrenda.capturada_por_id != user.pk


def puede_ver(user, ofrenda: OfrendaIglesia) -> bool:
    if tiene_permiso(user, "ofrendas.ver_todas") or ofrenda.capturada_por_id == user.pk:
        return True
    pendiente = ofrenda.estado != Ofrenda.Estado.AVALADA
    return pendiente and tiene_permiso(user, "ofrendas.iglesia_avalar")


def puede_administrar_catalogo(user) -> bool:
    return tiene_permiso(user, "ofrendas.catalogo")


def visibles(user):
    """Ofrendas de la iglesia que esta persona puede ver."""
    todas = OfrendaIglesia.objects.select_related("tipo", "capturada_por")
    if tiene_permiso(user, "ofrendas.ver_todas"):
        return todas
    filtro = Q(capturada_por=user)
    if tiene_permiso(user, "ofrendas.iglesia_avalar"):
        filtro |= ~Q(estado=Ofrenda.Estado.AVALADA)
    return todas.filter(filtro)


# ---------- catálogo ----------
def tipo_dict(t: TipoOfrenda) -> dict:
    return {
        "id": t.pk,
        "nombre": t.nombre,
        "para_grupo": t.para_grupo,
        "para_iglesia": t.para_iglesia,
        "activo": t.activo,
    }


def guardar_tipo(*, datos: dict, actor, tipo: TipoOfrenda | None = None, request=None):
    nombre = (datos.get("nombre", tipo.nombre if tipo else "") or "").strip()
    if not nombre:
        raise ValidationError("Escribe el nombre del tipo de ofrenda.")
    existe = TipoOfrenda.objects.filter(nombre__iexact=nombre)
    if tipo:
        existe = existe.exclude(pk=tipo.pk)
    if existe.exists():
        raise ValidationError("Ya existe un tipo de ofrenda con ese nombre.")
    para_grupo = datos.get("para_grupo", tipo.para_grupo if tipo else False)
    para_iglesia = datos.get("para_iglesia", tipo.para_iglesia if tipo else True)
    if not (para_grupo or para_iglesia):
        raise ValidationError("Marca dónde se usa: en los grupos, en la iglesia o en ambos.")
    nuevo = tipo is None
    tipo = tipo or TipoOfrenda()
    tipo.nombre, tipo.para_grupo, tipo.para_iglesia = nombre, para_grupo, para_iglesia
    tipo.activo = datos.get("activo", tipo.activo if tipo.pk else True)
    tipo.save()
    audit.log(
        "ofrenda.tipo_creado" if nuevo else "ofrenda.tipo_editado",
        actor=actor, target=tipo, request=request, nombre=nombre,
        para_grupo=para_grupo, para_iglesia=para_iglesia, activo=tipo.activo,
    )  # fmt: skip
    return tipo


# ---------- operaciones ----------
@transaction.atomic
def capturar(*, fecha, tipo, monto, nota, actor, request=None) -> OfrendaIglesia:
    monto = base._monto(monto)
    if not (tipo.activo and tipo.para_iglesia):
        raise ValidationError("Ese tipo de ofrenda no se usa en la iglesia.")
    if fecha > timezone.localdate():
        raise ValidationError("La fecha no puede ser futura.")
    ofrenda = OfrendaIglesia.objects.create(
        fecha=fecha, tipo=tipo, monto=monto, nota=(nota or "").strip(), capturada_por=actor
    )
    OfrendaIglesiaMovimiento.objects.create(
        ofrenda=ofrenda, tipo=OfrendaMovimiento.Tipo.CAPTURA, monto=monto, usuario=actor
    )
    audit.log(
        "ofrenda_iglesia.capturada", actor=actor, target=ofrenda, request=request,
        tipo=tipo.nombre, monto=str(monto),
    )  # fmt: skip
    return ofrenda


@transaction.atomic
def corregir(ofrenda: OfrendaIglesia, *, monto, motivo, actor, request=None) -> OfrendaIglesia:
    motivo = (motivo or "").strip()
    if not motivo:
        raise ValidationError("La corrección exige un motivo.")
    nuevo = base._monto(monto)
    anterior = ofrenda.monto
    ofrenda.monto = nuevo
    ofrenda.estado = Ofrenda.Estado.PENDIENTE  # requiere un nuevo aval
    ofrenda.save(update_fields=["monto", "estado"])
    OfrendaIglesiaMovimiento.objects.create(
        ofrenda=ofrenda, tipo=OfrendaMovimiento.Tipo.CORRECCION, monto_anterior=anterior,
        monto=nuevo, motivo=motivo, usuario=actor,
    )  # fmt: skip
    audit.log(
        "ofrenda_iglesia.corregida", actor=actor, target=ofrenda, request=request,
        anterior=str(anterior), nuevo=str(nuevo), motivo=motivo,
    )  # fmt: skip
    return ofrenda


@transaction.atomic
def avalar(ofrenda: OfrendaIglesia, *, monto_contado, actor, request=None) -> OfrendaIglesia:
    """El PIN ya fue verificado por quien llama."""
    if ofrenda.capturada_por_id == actor.pk:
        raise base.ElPropioCapturista
    contado = base._monto(monto_contado)
    diferencia = contado - ofrenda.monto
    ofrenda.estado = Ofrenda.Estado.AVALADA if diferencia == 0 else Ofrenda.Estado.DIFERENCIA
    ofrenda.save(update_fields=["estado"])
    OfrendaIglesiaMovimiento.objects.create(
        ofrenda=ofrenda, tipo=OfrendaMovimiento.Tipo.AVAL, monto_anterior=ofrenda.monto,
        monto=contado, diferencia=diferencia, usuario=actor,
    )  # fmt: skip
    audit.log(
        "ofrenda_iglesia.avalada" if diferencia == 0 else "ofrenda_iglesia.diferencia",
        actor=actor, target=ofrenda, request=request,
        capturado=str(ofrenda.monto), contado=str(contado), diferencia=str(diferencia),
    )  # fmt: skip
    return ofrenda


def ofrenda_iglesia_dict(o: OfrendaIglesia, *, detalle: bool = True) -> dict:
    datos = {
        "id": o.pk,
        "fecha": o.fecha.isoformat(),
        "grupo": "Iglesia",
        "tipo": o.tipo_id,
        "tipo_display": o.tipo.nombre,
        "concepto": o.nota,
        "monto": str(o.monto),
        "estado": o.estado,
        "estado_display": o.get_estado_display(),
        "con_diferencia": o.estado == Ofrenda.Estado.DIFERENCIA,
        "origen": "iglesia",
        "capturada_por": o.capturada_por.nombre if o.capturada_por else "",
    }
    if detalle:
        datos["movimientos"] = [
            {
                "tipo": m.tipo,
                "monto": str(m.monto),
                "diferencia": str(m.diferencia) if m.diferencia is not None else None,
                "motivo": m.motivo,
                "por": m.usuario.nombre if m.usuario else "",
                "fecha": m.creado_en.isoformat(),
            }
            for m in o.movimientos.select_related("usuario")
        ]
    return datos


# ---------- resumen financiero ----------
def _grupos_visibles(user) -> list[Grupo]:
    grupos = Grupo.objects.all()
    if tiene_permiso(user, "ofrendas.ver_todas"):
        return list(grupos)
    return [g for g in grupos if base.puede_ver_finanzas_grupo(user, g)]


def _filas_de_grupos(user, *, desde, hasta, tipo, grupo, estado) -> list[dict]:
    permitidos = _grupos_visibles(user)
    if grupo:
        permitidos = [g for g in permitidos if g.pk == grupo]
    qs = Ofrenda.objects.filter(reunion__grupo__in=permitidos).select_related(
        "reunion__grupo", "tipo_ofrenda"
    )
    if desde:
        qs = qs.filter(reunion__fecha__gte=desde)
    if hasta:
        qs = qs.filter(reunion__fecha__lte=hasta)
    if tipo:
        qs = qs.filter(tipo_ofrenda_id=tipo)
    if estado:
        qs = qs.filter(estado=estado)
    return [
        {
            "id": o.pk,
            "origen": "grupo",
            "origen_display": o.reunion.grupo.nombre,
            "fecha": o.reunion.fecha.isoformat(),
            "tipo": o.tipo_ofrenda.nombre if o.tipo_ofrenda else o.get_tipo_display(),
            "monto": o.monto,
            "estado": o.estado,
            "estado_display": o.get_estado_display(),
            "concepto": o.concepto,
        }
        for o in qs[:LIMITE_FILAS]
    ]


def _filas_de_iglesia(user, *, desde, hasta, tipo, estado) -> list[dict]:
    qs = visibles(user)
    if desde:
        qs = qs.filter(fecha__gte=desde)
    if hasta:
        qs = qs.filter(fecha__lte=hasta)
    if tipo:
        qs = qs.filter(tipo_id=tipo)
    if estado:
        qs = qs.filter(estado=estado)
    return [
        {
            "id": o.pk,
            "origen": "iglesia",
            "origen_display": "Iglesia",
            "fecha": o.fecha.isoformat(),
            "tipo": o.tipo.nombre,
            "monto": o.monto,
            "estado": o.estado,
            "estado_display": o.get_estado_display(),
            "concepto": o.nota,
        }
        for o in qs[:LIMITE_FILAS]
    ]


def resumen(user, *, desde=None, hasta=None, origen="", tipo=None, grupo=None, estado="") -> dict:
    """Filas, totales y series de lo que la persona puede ver, con filtros dinámicos."""
    filas: list[dict] = []
    if origen in ("", "grupo"):
        filas += _filas_de_grupos(
            user, desde=desde, hasta=hasta, tipo=tipo, grupo=grupo, estado=estado
        )
    if origen in ("", "iglesia") and not grupo:
        filas += _filas_de_iglesia(user, desde=desde, hasta=hasta, tipo=tipo, estado=estado)
    filas.sort(key=lambda f: (f["fecha"], f["id"]), reverse=True)

    total = sum((f["monto"] for f in filas), CERO)
    avalado = sum((f["monto"] for f in filas if f["estado"] == Ofrenda.Estado.AVALADA), CERO)
    por_origen: dict[str, Decimal] = defaultdict(Decimal)
    por_tipo: dict[str, Decimal] = defaultdict(Decimal)
    por_mes: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    for f in filas:
        por_origen[f["origen"]] += f["monto"]
        por_tipo[f["tipo"]] += f["monto"]
        por_mes[f["fecha"][:7]][f["origen"]] += f["monto"]

    return {
        "filas": [{**f, "monto": str(f["monto"])} for f in filas],
        "truncado": len(filas) >= LIMITE_FILAS,
        "totales": {
            "total": str(total),
            "avalado": str(avalado),
            "por_avalar": str(total - avalado),
            "cantidad": len(filas),
            "grupo": str(por_origen.get("grupo", CERO)),
            "iglesia": str(por_origen.get("iglesia", CERO)),
        },
        "por_tipo": [
            {"tipo": t, "monto": str(m)} for t, m in sorted(por_tipo.items(), key=lambda x: -x[1])
        ],
        "por_mes": [
            {"mes": mes, "grupo": str(v.get("grupo", CERO)), "iglesia": str(v.get("iglesia", CERO))}
            for mes, v in sorted(por_mes.items())
        ],
    }
