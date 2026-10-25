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
    "peticiones.dias_retencion": {
        "default": 30,
        "tipo": "entero",
        "descripcion": "Días que se conservan las peticiones de oración antes de borrarse",
    },
    "peticiones.visibilidad_por_defecto": {
        "default": "lideres",
        "tipo": "opcion",
        "opciones": ["lideres", "grupo", "equipo"],
        "descripcion": "Alcance por defecto de una petición nueva (líderes, grupo o equipo)",
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
    if tipo == "opcion":
        if valor not in definicion(clave)["opciones"]:
            raise ValidationError("La opción no es válida.")
        return valor
    if tipo == "entero":
        if isinstance(valor, bool) or not isinstance(valor, (int, float)) or int(valor) != valor:
            raise ValidationError("El valor debe ser un número entero.")
        if not 1 <= valor <= 3650:
            raise ValidationError("Debe estar entre 1 y 3650 días.")
        return int(valor)
    raise ValidationError("Tipo de parámetro no soportado.")
