from django.conf import settings
from django.db import models


class Mensaje(models.Model):
    origen_tipo = models.CharField(max_length=40, db_index=True)
    origen_id = models.PositiveIntegerField()
    origen_etiqueta = models.CharField(max_length=250)  # texto fijo con el que se publicó
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    autor_nombre = models.CharField(max_length=150)  # se conserva aunque cambie la cuenta
    texto = models.TextField(max_length=1000)
    fijado = models.BooleanField(default=False)
    eliminado = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-fijado", "-creado_en"]
        indexes = [models.Index(fields=["origen_tipo", "origen_id"], name="tablero_origen_idx")]

    def __str__(self):
        return f"{self.origen_etiqueta} · {self.autor_nombre}"


class Lectura(models.Model):
    """Hasta cuándo vio cada persona el tablero de un origen (para contar no leídos)."""

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+"
    )
    origen_tipo = models.CharField(max_length=40)
    origen_id = models.PositiveIntegerField()
    visto_hasta = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "origen_tipo", "origen_id"], name="tablero_lectura_unica"
            )
        ]

    def __str__(self):
        return f"{self.usuario_id} · {self.origen_tipo}:{self.origen_id}"
