from django.conf import settings
from django.db import models


class Formulario(models.Model):
    """Campos adicionales de una entidad (persona, grupo…), versionados (CFG-01, CFG-06, CFG-08).

    Cada cambio crea una versión nueva. Un campo nunca se borra: se desactiva, y las respuestas
    que ya se guardaron se conservan.
    """

    entidad = models.CharField(max_length=20)
    version = models.PositiveIntegerField()
    campos = models.JSONField(default=list)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["entidad", "-version"]
        constraints = [
            models.UniqueConstraint(fields=["entidad", "version"], name="formulario_version_unica")
        ]
        verbose_name = "formulario"
        verbose_name_plural = "formularios"

    def __str__(self):
        return f"{self.entidad} v{self.version}"
