from django.db import models
from django.utils import timezone

from apps.personas.models import Persona


class Unidad(models.Model):
    """Área de servicio de la iglesia: cafetería, librería, niños, danza, etc."""

    nombre = models.CharField(max_length=120, unique=True)
    descripcion = models.CharField(max_length=300, blank=True)
    activa = models.BooleanField(default=True)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name_plural = "unidades"

    def __str__(self):
        return self.nombre


class UnidadMiembro(models.Model):
    """Persona dentro de una unidad con su rol. Cada rol vale solo dentro de esa unidad."""

    class Rol(models.TextChoices):
        ENCARGADO = "encargado", "Encargado"
        RESPALDO = "respaldo", "Respaldo"
        SERVIDOR = "servidor", "Servidor"

    unidad = models.ForeignKey(Unidad, on_delete=models.CASCADE, related_name="miembros")
    persona = models.ForeignKey(Persona, on_delete=models.PROTECT, related_name="unidades")
    rol = models.CharField(max_length=12, choices=Rol.choices, default=Rol.SERVIDOR)
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
        return f"{self.persona} · {self.get_rol_display()} · {self.unidad}"
