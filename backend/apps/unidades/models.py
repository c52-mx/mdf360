from django.db import models
from django.utils import timezone

from apps.personas.models import Persona


class Unidad(models.Model):
    """Ministerio: área de servicio de la iglesia (cafetería, librería, niños, danza, etc.)."""

    nombre = models.CharField(max_length=120, unique=True)
    descripcion = models.CharField(max_length=300, blank=True)
    activa = models.BooleanField(default=True)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "ministerio"
        verbose_name_plural = "ministerios"

    def __str__(self):
        return self.nombre


class UnidadMiembro(models.Model):
    """Persona dentro de un ministerio con su rol. Cada rol vale solo dentro de ese ministerio."""

    class Rol:
        """Claves de los roles base; los roles y sus permisos se configuran en RolEquipo."""

        ENCARGADO = "encargado"
        RESPALDO = "respaldo"
        SERVIDOR = "servidor"

    unidad = models.ForeignKey(Unidad, on_delete=models.CASCADE, related_name="miembros")
    persona = models.ForeignKey(Persona, on_delete=models.PROTECT, related_name="unidades")
    rol = models.CharField(max_length=40, default=Rol.SERVIDOR)
    activo = models.BooleanField(default=True)
    desde = models.DateField(default=timezone.localdate)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["unidad", "persona", "rol"], name="unidad_miembro_unico"
            )
        ]
        ordering = ["unidad", "rol", "persona__nombre"]

    def __str__(self):
        return f"{self.persona} · {self.rol} · {self.unidad}"
