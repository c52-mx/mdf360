import os
import uuid
from datetime import date

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.accounts.phone import normalize_whatsapp


class Nivel(models.TextChoices):
    CONTACTO = "contacto", "Contacto"
    PARTICIPANTE = "participante", "Participante"
    EDU = "edu", "Expediente completo"


NIVEL_ORDEN = {Nivel.CONTACTO: 0, Nivel.PARTICIPANTE: 1, Nivel.EDU: 2}


class Procedencia(models.TextChoices):
    MIEMBRO = "miembro", "Miembro de la iglesia"
    INVITADO_GRUPO = "invitado_grupo", "Invitado de grupo"
    VISITANTE = "visitante", "Visitante"
    EXTERNO = "externo", "Externo"


def foto_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower() or ".jpg"
    return f"personas/{instance.pk}/{uuid.uuid4().hex}{ext}"


class Persona(models.Model):
    """Persona de la iglesia. Una sola entidad con tres niveles de registro (M1-12).

    Los campos siguen la «Radiografía de miembros GC». Grupo, líder y sector son texto
    provisional: en el módulo Grupos (Sprint 3) pasan a ser relaciones.
    """

    nivel = models.CharField(max_length=20, choices=Nivel.choices, default=Nivel.CONTACTO)
    procedencia = models.CharField(
        max_length=20, choices=Procedencia.choices, default=Procedencia.VISITANTE
    )
    activo = models.BooleanField(default=True)

    # Datos personales
    nombre = models.CharField(max_length=100)
    apellido_paterno = models.CharField(max_length=100, blank=True)
    apellido_materno = models.CharField(max_length=100, blank=True)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    foto = models.ImageField(upload_to=foto_path, blank=True)

    # Contacto y domicilio
    whatsapp = models.CharField("Celular / WhatsApp", max_length=16, blank=True)
    telefono_fijo = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    calle_numero = models.CharField("calle y número", max_length=200, blank=True)
    colonia = models.CharField(max_length=100, blank=True)
    codigo_postal = models.CharField(max_length=10, blank=True)
    alcaldia = models.CharField("alcaldía o municipio", max_length=100, blank=True)

    # Grupo de conexión (provisional, texto)
    sector = models.CharField(max_length=100, blank=True)
    grupo_conexion = models.CharField(max_length=150, blank=True)
    lider = models.CharField("líder", max_length=150, blank=True)

    # Vida en la iglesia
    miembro_desde = models.DateField(null=True, blank=True)
    sirve_en_ministerio = models.BooleanField(default=False)
    ministerios = models.TextField("ministerio(s) en que sirve", blank=True)
    devocional_personal = models.CharField(max_length=200, blank=True)
    oracion_familias = models.BooleanField(
        "Oración de Familias en Acción (miércoles)", default=False
    )
    oracion_familias_detalle = models.CharField(max_length=200, blank=True)
    otros_cursos = models.TextField(blank=True)
    observaciones = models.TextField(blank=True)

    # Campos del diseñador de formularios (CFG-06)
    datos_extra = models.JSONField(default=dict, blank=True)

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="persona",
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["apellido_paterno", "apellido_materno", "nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["whatsapp"], condition=~models.Q(whatsapp=""), name="persona_whatsapp_unico"
            )
        ]
        indexes = [models.Index(fields=["nivel", "activo"])]

    def __str__(self):
        return self.nombre_completo

    def save(self, *args, **kwargs):
        if self.whatsapp:
            self.whatsapp = normalize_whatsapp(self.whatsapp)
        self.email = (self.email or "").strip().lower()
        super().save(*args, **kwargs)

    @property
    def nombre_completo(self) -> str:
        partes = [self.nombre, self.apellido_paterno, self.apellido_materno]
        return " ".join(p for p in partes if p)

    @property
    def edad(self) -> int | None:
        if not self.fecha_nacimiento:
            return None
        hoy = date.today()
        cumplio = (hoy.month, hoy.day) >= (self.fecha_nacimiento.month, self.fecha_nacimiento.day)
        return hoy.year - self.fecha_nacimiento.year - (0 if cumplio else 1)


class ProcesoDiscipular(models.Model):
    """Catálogo configurable de los procesos de desarrollo discipular."""

    nombre = models.CharField(max_length=120, unique=True)
    orden = models.PositiveSmallIntegerField(default=0)
    pide_maestro = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["orden", "nombre"]
        verbose_name = "proceso discipular"
        verbose_name_plural = "procesos discipulares"

    def __str__(self):
        return self.nombre


class PersonaProceso(models.Model):
    persona = models.ForeignKey(Persona, on_delete=models.CASCADE, related_name="procesos")
    proceso = models.ForeignKey(ProcesoDiscipular, on_delete=models.PROTECT, related_name="+")
    completado = models.BooleanField(default=False)
    fecha = models.DateField(null=True, blank=True)
    maestro = models.CharField("nombre del maestro", max_length=120, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["persona", "proceso"], name="persona_proceso_unico")
        ]

    def __str__(self):
        return f"{self.persona} · {self.proceso}"


class Consentimiento(models.Model):
    """Aceptación del aviso de privacidad (M1-11), ligada a la versión del texto."""

    persona = models.ForeignKey(Persona, on_delete=models.CASCADE, related_name="consentimientos")
    version = models.CharField(max_length=40)
    acepta_datos = models.BooleanField()
    acepta_foto = models.BooleanField(default=False)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.persona} · aviso {self.version}"


class PersonaMovimiento(models.Model):
    """Historial de altas, bajas y cambios con fecha y motivo (M1-14)."""

    class Tipo(models.TextChoices):
        ALTA = "alta", "Alta"
        CAMBIO_NIVEL = "cambio_nivel", "Cambio de nivel de registro"
        BAJA = "baja", "Baja"
        REACTIVACION = "reactivacion", "Reactivación"
        OTRO = "otro", "Otro"

    persona = models.ForeignKey(Persona, on_delete=models.CASCADE, related_name="movimientos")
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    fecha = models.DateField(default=timezone.localdate)
    motivo = models.CharField(max_length=300, blank=True)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha", "-creado_en"]

    def __str__(self):
        return f"{self.persona} · {self.get_tipo_display()} · {self.fecha}"
