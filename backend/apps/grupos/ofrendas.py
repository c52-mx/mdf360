"""Ofrendas del grupo con aval del Tesorero (M3-04).

Reglas (matriz de confidencialidad aprobada, v3.2, sec. 3.3):
- El Secretario captura. Si el grupo no tiene Secretario, el Líder lo suple. Líder y Supervisor
  consultan; el Pastor consulta todo.
- El Anciano no ve finanzas.
- El Tesorero cuenta, escribe su cifra y confirma con su PIN (aval electrónico simple). Si el
  grupo no tiene Tesorero, lo suple el Líder o el Pastor. Toda suplencia queda en bitácora.
- Una ofrenda avalada no se edita sin motivo; la corrección exige un nuevo aval.
- Quien capturó no puede avalar su propia captura.
"""

from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.accounts.permissions import tiene_permiso
from apps.core import audit, config

from .access import roles_en
from .models import GrupoMiembro, Ofrenda, OfrendaMovimiento, Reunion

R = GrupoMiembro.Rol


# ---------- permisos ----------
def _tiene_activo(grupo, rol) -> bool:
    return GrupoMiembro.objects.filter(grupo=grupo, rol=rol, activo=True).exists()


def captura_suplente(user, reunion: Reunion) -> bool:
    """El Líder captura cuando el grupo no tiene Secretario."""
    roles = roles_en(user, reunion.grupo)
    return (
        R.LIDER in roles
        and R.SECRETARIO not in roles
        and not _tiene_activo(reunion.grupo, R.SECRETARIO)
    )


def puede_capturar_ofrenda(user, reunion: Reunion) -> bool:
    if tiene_permiso(user, "grupos.gestionar"):
        return True
    if reunion.fecha != date.today():
        return False
    return R.SECRETARIO in roles_en(user, reunion.grupo) or captura_suplente(user, reunion)


def aval_suplente(user, grupo) -> bool:
    """Sin Tesorero en el grupo, avalan el Líder o el Pastor."""
    if _tiene_activo(grupo, R.TESORERO):
        return False
    return R.LIDER in roles_en(user, grupo) or tiene_permiso(user, "grupos.gestionar")


def puede_avalar(user, grupo) -> bool:
    return R.TESORERO in roles_en(user, grupo) or aval_suplente(user, grupo)


def puede_ver_ofrendas(user, reunion: Reunion) -> bool:
    return puede_ver_finanzas_grupo(user, reunion.grupo, reunion.fecha)


def puede_ver_finanzas_grupo(user, grupo, fecha=None) -> bool:
    if tiene_permiso(user, "ofrendas.ver_todas"):
        return True
    roles = roles_en(user, grupo)
    if roles & {R.LIDER, R.SUPERVISOR, R.TESORERO}:
        return True
    return R.SECRETARIO in roles and fecha == date.today()


def puede_corregir(user, ofrenda: Ofrenda) -> bool:
    return puede_capturar_ofrenda(user, ofrenda.reunion)


def diferencias_visibles(user, grupo) -> int | None:
    """Cantidad de ofrendas «Con diferencia» del grupo, solo si el usuario puede ver finanzas."""
    if not puede_ver_finanzas_grupo(user, grupo):
        return None
    return Ofrenda.objects.filter(reunion__grupo=grupo, estado=Ofrenda.Estado.DIFERENCIA).count()


# ---------- operaciones ----------
class ElPropioCapturista(Exception):
    pass


def _monto(valor) -> Decimal:
    try:
        monto = Decimal(str(valor)).quantize(Decimal("0.01"))
    except Exception as exc:
        raise ValidationError("El monto no es válido.") from exc
    maximo = config.obtener_monto("ofrendas.monto_maximo")
    if monto <= 0 or monto > maximo:
        raise ValidationError(f"El monto debe ser mayor que cero y no pasar de {maximo:,.2f}.")
    return monto


@transaction.atomic
def capturar(reunion, *, tipo, concepto, monto, actor, request=None) -> Ofrenda:
    monto = _monto(monto)
    concepto = (concepto or "").strip()
    if tipo == Ofrenda.Tipo.ESPECIAL and not concepto:
        raise ValidationError("Escribe el concepto de la ofrenda especial.")
    if tipo == Ofrenda.Tipo.REGULAR:
        concepto = ""
    repetida = Ofrenda.objects.filter(reunion=reunion, tipo=tipo, concepto=concepto).exists()
    unica = tipo == Ofrenda.Tipo.ESPECIAL or config.obtener("ofrendas.una_regular_por_reunion")
    if repetida and unica:
        raise ValidationError(
            "Ya hay una ofrenda de este tipo en la reunión. Corrígela con motivo."
        )
    suplencia = captura_suplente(actor, reunion)
    ofrenda = Ofrenda.objects.create(
        reunion=reunion, tipo=tipo, concepto=concepto, monto=monto, capturada_por=actor
    )
    OfrendaMovimiento.objects.create(
        ofrenda=ofrenda, tipo="captura", monto=monto, usuario=actor,
        motivo="Captura como suplente del Secretario" if suplencia else "",
    )  # fmt: skip
    audit.log(
        "ofrenda.capturada", actor=actor, target=ofrenda, request=request,
        tipo=tipo, monto=str(monto), suplencia=suplencia,
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
    suplencia = captura_suplente(actor, ofrenda.reunion)
    OfrendaMovimiento.objects.create(
        ofrenda=ofrenda, tipo="correccion", monto_anterior=anterior, monto=nuevo,
        motivo=motivo, usuario=actor,
    )  # fmt: skip
    audit.log(
        "ofrenda.corregida", actor=actor, target=ofrenda, request=request,
        anterior=str(anterior), nuevo=str(nuevo), motivo=motivo, suplencia=suplencia,
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
    suplencia = R.TESORERO not in roles_en(actor, ofrenda.reunion.grupo)
    OfrendaMovimiento.objects.create(
        ofrenda=ofrenda, tipo="aval", monto_anterior=ofrenda.monto, monto=contado,
        diferencia=diferencia, usuario=actor,
        motivo="Aval como suplente del Tesorero" if suplencia else "",
    )  # fmt: skip
    audit.log(
        "ofrenda.avalada" if diferencia == 0 else "ofrenda.diferencia",
        actor=actor, target=ofrenda, request=request,
        capturado=str(ofrenda.monto), contado=str(contado), diferencia=str(diferencia),
        suplencia=suplencia,
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
        "con_diferencia": o.estado == Ofrenda.Estado.DIFERENCIA,
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
