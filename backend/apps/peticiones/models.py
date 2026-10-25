from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class OrigenInmutable(Exception):
    """Se intentó cambiar el origen de una petición ya registrada."""


class FormularioPeticion(models.Model):
    """Definición versionada del formulario de peticiones (campos configurables, CFG-01/08).

    Cada cambio crea una versión nueva; las peticiones guardan la versión con que se capturaron.
    Los campos nunca se borran: se desactivan, para no perder las respuestas antiguas.
    """

    version = models.PositiveIntegerField(unique=True)
    campos = models.JSONField(default=list)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version"]
        verbose_name = "formulario de peticiones"
        verbose_name_plural = "formularios de peticiones"

    def __str__(self):
        return f"Formulario v{self.version}"


class Peticion(models.Model):
    class Estado(models.TextChoices):
        ACTIVA = "activa", "Activa"
        ATENDIDA = "atendida", "Atendida"

    class Visibilidad(models.TextChoices):
        LIDERES = "lideres", "Solo líderes"
        GRUPO = "grupo", "Mi grupo"
        EQUIPO = "equipo", "Equipo de oración"

    # --- Origen: siempre presente e inmutable (de dónde viene la petición) ---
    origen_tipo = models.CharField(max_length=40, db_index=True)
    origen_id = models.PositiveIntegerField()
    origen_etiqueta = models.CharField(max_length=250)  # texto fijo, sobrevive a renombres
    referencia_id = models.PositiveIntegerField(null=True, blank=True)  # ej. la reunión

    # --- Contenido: todo cifrado ---
    formulario_version = models.PositiveIntegerField()
    datos_cifrados = models.TextField()

    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.ACTIVA)
    # Quién puede leerla: lo elige quien la registra (con autorización de quien la pide)
    visibilidad = models.CharField(
        max_length=20, choices=Visibilidad.choices, default=Visibilidad.LIDERES
    )
    # Si es verdadero, los campos que identifican a la persona se ocultan a quien no es líder
    ocultar_nombre = models.BooleanField(default=False)
    creada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    creada_en = models.DateTimeField(auto_now_add=True)
    expira_en = models.DateTimeField(db_index=True)
    atendida_en = models.DateTimeField(null=True, blank=True)
    atendida_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["-creada_en"]
        indexes = [models.Index(fields=["origen_tipo", "origen_id"], name="peticiones_origen_idx")]

    CAMPOS_DE_ORIGEN = ("origen_tipo", "origen_id", "origen_etiqueta", "referencia_id")

    def __str__(self):
        return f"Petición {self.pk} · {self.origen_etiqueta}"

    def save(self, *args, **kwargs):
        if self.pk:
            original = Peticion.objects.filter(pk=self.pk).values(*self.CAMPOS_DE_ORIGEN).first()
            if original is not None and any(
                original[c] != getattr(self, c) for c in self.CAMPOS_DE_ORIGEN
            ):
                raise OrigenInmutable("El origen de una petición no se puede cambiar.")
        super().save(*args, **kwargs)

    @staticmethod
    def calcular_expiracion(dias: int):
        return timezone.now() + timedelta(days=dias)
