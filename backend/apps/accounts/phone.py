import re

from django.core.exceptions import ValidationError

DEFAULT_COUNTRY_CODE = "52"  # México


def normalize_whatsapp(raw: str) -> str:
    """Devuelve el número en formato E.164 (+52XXXXXXXXXX).

    Acepta espacios, guiones y paréntesis. Un número de 10 dígitos se toma como mexicano.
    El número es el identificador del usuario y sirve para detectar duplicados (M1-12).
    """
    if raw is None:
        raise ValidationError("El número de WhatsApp es obligatorio.")
    digits = re.sub(r"[^\d+]", "", str(raw))
    has_plus = digits.startswith("+")
    digits = digits.lstrip("+")
    if not has_plus:
        if len(digits) == 10:
            digits = DEFAULT_COUNTRY_CODE + digits
        elif digits.startswith("00"):
            digits = digits[2:]
    if not 11 <= len(digits) <= 15:
        raise ValidationError("El número de WhatsApp no es válido.")
    return "+" + digits
