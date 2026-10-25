"""Parámetros configurables del sistema (principio low-code: ajustar sin tocar código).

Cada parámetro tiene un valor por defecto aquí; el valor vigente se guarda en la base de datos
(modelo Configuracion) y se edita desde la pantalla «Configuración». Cada cambio queda en bitácora.
"""

from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError

DEFINICIONES = {
    "ofrendas.monto_maximo": {
        "default": 1000000,
        "tipo": "monto",
        "descripcion": "Monto máximo permitido por ofrenda (MXN)",
    },
    "ofrendas.una_regular_por_reunion": {
        "default": True,
        "tipo": "booleano",
        "descripcion": "Permitir una sola ofrenda regular por reunión",
    },
}


def definicion(clave: str) -> dict:
    if clave not in DEFINICIONES:
        raise KeyError(clave)
    return DEFINICIONES[clave]


def obtener(clave: str):
    from .models import Configuracion

    fila = Configuracion.objects.filter(clave=clave).first()
    return fila.valor if fila is not None else definicion(clave)["default"]


def obtener_monto(clave: str) -> Decimal:
    return Decimal(str(obtener(clave)))


def validar(clave: str, valor):
    """Devuelve el valor normalizado o lanza ValidationError."""
    tipo = definicion(clave)["tipo"]
    if tipo == "booleano":
        if not isinstance(valor, bool):
            raise ValidationError("El valor debe ser verdadero o falso.")
        return valor
    if tipo == "monto":
        if isinstance(valor, bool):
            raise ValidationError("El valor debe ser un número.")
        try:
            numero = Decimal(str(valor))
        except InvalidOperation as exc:
            raise ValidationError("El valor debe ser un número.") from exc
        if numero <= 0 or numero > Decimal("1000000000"):
            raise ValidationError("El monto debe ser mayor que cero y menor a 1,000,000,000.")
        return int(numero) if numero == numero.to_integral() else float(numero)
    raise ValidationError("Tipo de parámetro no soportado.")
