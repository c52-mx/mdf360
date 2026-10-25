"""Ofrendas del grupo con aval del Tesorero (M3-04).

Reglas (matriz de confidencialidad aprobada, v3.2, sec. 3.3):
- El Secretario captura. Líder y Supervisor solo consultan; el Pastor consulta todo.
- El Anciano no ve finanzas.
- El Tesorero cuenta, escribe su cifra y confirma con su PIN (aval electrónico simple).
- Una ofrenda avalada no se edita sin motivo; la corrección exige un nuevo aval.
- Quien capturó no puede avalar su propia captura.
"""

from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.accounts.permissions import tiene_permiso
from apps.core import audit

from .access import roles_en
from .models import GrupoMiembro, Ofrenda, OfrendaMovimiento, Reunion

R = GrupoMiembro.Rol
MONTO_MAXIMO = Decimal("1000000")


# ---------- permisos ----------
def puede_capturar_ofrenda(user, reunion: Reunion) -> bool:
    if tiene_permiso(user, "grupos.gestionar"):
        return True
    return R.SECRETARIO in roles_en(user, reunion.grupo) and reunion.fecha == date.today()


def puede_avalar(user, grupo) -> bool:
    return R.TESORERO in roles_en(user, grupo)


def puede_ver_ofrendas(user, reunion: Reunion) -> bool:
    if tiene_permiso(user, "ofrendas.ver_todas"):
        return True
    roles = roles_en(user, reunion.grupo)
    if roles & {R.LIDER, R.SUPERVISOR, R.TESORERO}:
        return True
    return R.SECRETARIO in roles and reunion.fecha == date.today()


def puede_corregir(user, ofrenda: Ofrenda) -> bool:
    return puede_capturar_ofrenda(user, ofrenda.reunion)


# ---------- operaciones ----------
class ElPropioCapturista(Exception):
    pass


def _monto(valor) -> Decimal:
    try:
        monto = Decimal(str(valor)).quantize(Decimal("0.01"))
    except Exception as exc:
        raise ValidationError("El monto no es válido.") from exc
    if monto <= 0 or monto > MONTO_MAXIMO:
        raise ValidationError("El monto debe ser mayor que cero y menor a 1,000,000.")
    return monto


@transaction.atomic
def capturar(reunion, *, tipo, concepto, monto, actor, request=None) -> Ofrenda:
    monto = _monto(monto)
    concepto = (concepto or "").strip()
    if tipo == Ofrenda.Tipo.ESPECIAL and not concepto:
        raise ValidationError("Escribe el concepto de la ofrenda especial.")
    if tipo == Ofrenda.Tipo.REGULAR:
        concepto = ""
    if Ofrenda.objects.filter(reunion=reunion, tipo=tipo, concepto=concepto).exists():
        raise ValidationError(
            "Ya hay una ofrenda de este tipo en la reunión. Corrígela con motivo."
        )
    ofrenda = Ofrenda.objects.create(
        reunion=reunion, tipo=tipo, concepto=concepto, monto=monto, capturada_por=actor
    )
    OfrendaMovimiento.objects.create(ofrenda=ofrenda, tipo="captura", monto=monto, usuario=actor)
    audit.log(
        "ofrenda.capturada", actor=actor, target=ofrenda, request=request,
        tipo=tipo, monto=str(monto),
    )  # fmt: skip
    return ofrenda


@transaction.atomic
def corregir(ofrenda: Ofrenda, *, monto, motivo, actor, request=None) -> Ofrenda:
    motivo = (motivo or "").strip()
    if not motivo:
        raise ValidationError("La corrección exige un motivo.")
    nuevo = _monto(monto)
    anterior = ofrenda.monto
    ofrenda.monto = nuevo
    ofrenda.estado = Ofrenda.Estado.PENDIENTE  # requiere un nuevo aval
    ofrenda.save(update_fields=["monto", "estado"])
    OfrendaMovimiento.objects.create(
        ofrenda=ofrenda, tipo="correccion", monto_anterior=anterior, monto=nuevo,
        motivo=motivo, usuario=actor,
    )  # fmt: skip
    audit.log(
        "ofrenda.corregida", actor=actor, target=ofrenda, request=request,
        anterior=str(anterior), nuevo=str(nuevo), motivo=motivo,
    )  # fmt: skip
    return ofrenda


@transaction.atomic
def avalar(ofrenda: Ofrenda, *, monto_contado, actor, request=None) -> Ofrenda:
    """El PIN ya fue verificado por quien llama. Registra la cifra contada y la diferencia."""
    if ofrenda.capturada_por_id == actor.pk:
        raise ElPropioCapturista
    contado = _monto(monto_contado)
    diferencia = contado - ofrenda.monto
    ofrenda.estado = Ofrenda.Estado.AVALADA if diferencia == 0 else Ofrenda.Estado.DIFERENCIA
    ofrenda.save(update_fields=["estado"])
    OfrendaMovimiento.objects.create(
        ofrenda=ofrenda, tipo="aval", monto_anterior=ofrenda.monto, monto=contado,
        diferencia=diferencia, usuario=actor,
    )  # fmt: skip
    audit.log(
        "ofrenda.avalada" if diferencia == 0 else "ofrenda.diferencia",
        actor=actor, target=ofrenda, request=request,
        capturado=str(ofrenda.monto), contado=str(contado), diferencia=str(diferencia),
    )  # fmt: skip
    return ofrenda


def ofrenda_dict(o: Ofrenda, *, detalle: bool = True) -> dict:
    base = {
        "id": o.pk,
        "reunion_id": o.reunion_id,
        "fecha": o.reunion.fecha.isoformat(),
        "grupo": o.reunion.grupo.nombre,
        "tipo": o.tipo,
        "tipo_display": o.get_tipo_display(),
        "concepto": o.concepto,
        "monto": str(o.monto),
        "estado": o.estado,
        "estado_display": o.get_estado_display(),
    }
    if detalle:
        base["movimientos"] = [
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
    return base
