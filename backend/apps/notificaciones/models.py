from django.conf import settings
from django.db import models


class Suscripcion(models.Model):
    """Un dispositivo (navegador o app instalada) que aceptó recibir notificaciones push."""

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="suscripciones_push"
    )
    endpoint = models.TextField(unique=True)
    p256dh = models.CharField(max_length=200)
    auth = models.CharField(max_length=100)
    agente = models.CharField(max_length=200, blank=True)
    creada_en = models.DateTimeField(auto_now_add=True)
    ultimo_envio = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "suscripción push"
        verbose_name_plural = "suscripciones push"

    def __str__(self):
        return f"{self.usuario_id} · {self.endpoint[:40]}"
