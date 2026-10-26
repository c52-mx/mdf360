import base64

from cryptography.hazmat.primitives import serialization
from django.core.management.base import BaseCommand
from py_vapid import Vapid01


def _b64(datos: bytes) -> str:
    return base64.urlsafe_b64encode(datos).rstrip(b"=").decode()


class Command(BaseCommand):
    help = "Genera un par de claves VAPID para las notificaciones push (se guardan como variables)."

    def handle(self, *args, **options):
        v = Vapid01()
        v.generate_keys()
        privada = v.private_key.private_numbers().private_value.to_bytes(32, "big")
        publica = v.public_key.public_bytes(
            serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
        )
        self.stdout.write(f"VAPID_PUBLIC_KEY={_b64(publica)}")
        self.stdout.write(f"VAPID_PRIVATE_KEY={_b64(privada)}")
