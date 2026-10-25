"""Cifrado a nivel de campo de las peticiones (NF-02).

Todo el contenido de una petición se guarda cifrado (Fernet: AES-128-CBC + HMAC). Ni el panel de
administración técnica ni una copia de la base de datos muestran el texto.

Claves: PETICIONES_ENCRYPTION_KEYS (separadas por coma; la primera cifra, todas descifran, lo que
permite rotarlas). Si no se define, se deriva de DJANGO_SECRET_KEY: en producción conviene definir
una clave propia, porque cambiar la clave de Django haría ilegibles las peticiones guardadas.
"""

import base64
import hashlib
import json

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings


def _claves() -> list[bytes]:
    crudas = [
        k.strip()
        for k in getattr(settings, "PETICIONES_ENCRYPTION_KEYS", "").split(",")
        if k.strip()
    ]
    if crudas:
        return [k.encode() for k in crudas]
    derivada = hashlib.sha256(f"peticiones:{settings.SECRET_KEY}".encode()).digest()
    return [base64.urlsafe_b64encode(derivada)]


def _fernet() -> MultiFernet:
    return MultiFernet([Fernet(k) for k in _claves()])


def cifrar(datos: dict) -> str:
    return _fernet().encrypt(json.dumps(datos, ensure_ascii=False).encode()).decode()


class NoSePuedeDescifrar(Exception):
    pass


def descifrar(texto: str) -> dict:
    try:
        return json.loads(_fernet().decrypt(texto.encode()).decode())
    except (InvalidToken, ValueError) as exc:
        raise NoSePuedeDescifrar from exc
