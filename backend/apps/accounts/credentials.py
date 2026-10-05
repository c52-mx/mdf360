import re

from django.core.exceptions import ValidationError

STRONG_MIN_LENGTH = 10
_PIN_RE = re.compile(r"^\d{6}$")
_SEQUENCES = ("0123456789", "9876543210")


def _is_trivial_pin(pin: str) -> bool:
    if len(set(pin)) == 1:
        return True
    return any(pin in seq for seq in _SEQUENCES)


def validate_credential(raw: str, strong: bool) -> None:
    """PIN de 6 dígitos para miembros; contraseña de 10+ caracteres para roles sensibles."""
    raw = raw or ""
    if strong:
        if len(raw) < STRONG_MIN_LENGTH:
            raise ValidationError(
                f"Tu rol requiere una contraseña de al menos {STRONG_MIN_LENGTH} caracteres."
            )
        if raw.isdigit() or len(set(raw)) < 4:
            raise ValidationError("La contraseña es demasiado simple; mezcla letras y números.")
        return
    if not _PIN_RE.match(raw):
        raise ValidationError("El PIN debe tener exactamente 6 números.")
    if _is_trivial_pin(raw):
        raise ValidationError("Elige un PIN menos obvio (evita 111111 o 123456).")
