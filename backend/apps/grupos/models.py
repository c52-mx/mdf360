import os
import uuid
from datetime import date, timedelta

from django.conf import settings
from django.db import models

from apps.personas.models import Persona


class Grupo(models.Model):
    """Grupo de Conexión (célula) o la reunión general de líderes."""

    class Tipo(models.TextChoices):
        CONEXION = "conexion", "Grupo de Conexión"
        LIDERES = "lideres", "Reunión general de líderes"

    nombre = models.CharField(max_length=150)
    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.CONEXION)
    sector = models.CharField(max_length=100, blank=True)
    colonia = models.CharField("zona o colonia", max_length=100, blank=True)
    dia_semana = models.PositiveSmallIntegerField(
        "día de la semana", null=True, blank=True, help_text="0 = lunes … 6 = domingo"
    )
    hora = models.TimeField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class GrupoMiembro(models.Model):
    """Persona dentro de un grupo, con su rol (M3-01). Los invitados son Contactos."""

    class Rol(models.TextChoices):
        SUPERVISOR = "supervisor", "Supervisor"
        LIDER = "lider", "Líder"
        SECRETARIO = "secretario", "Secretario"
        ANFITRION = "anfitrion", "Anfitrión"
        TESORERO = "tesorero", "Tesorero"
        ASISTENTE = "asistente", "Asistente"

    grupo = models.ForeignKey(Grupo, on_delete=models.CASCADE, related_name="miembros")
    persona = models.ForeignKey(Persona, on_delete=models.PROTECT, related_name="membresias")
    rol = models.CharField(max_length=20, choices=Rol.choices, default=Rol.ASISTENTE)
    activo = models.BooleanField(default=True)
    desde = models.DateField(default=date.today)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["grupo", "persona", "rol"], name="miembro_rol_unico")
        ]
        ordering = ["grupo", "rol", "persona__nombre"]

    def __str__(self):
        return f"{self.persona} · {self.get_rol_display()} · {self.grupo}"


def _archivo_estudio(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"estudios/{instance.semana.isoformat()}/{uuid.uuid4().hex}{ext}"


def lunes_de(dia: date) -> date:
    return dia - timedelta(days=dia.weekday())


class EstudioSemanal(models.Model):
    """Estudio de la semana (M3-02): PDF para adultos, PDF para niños y audio de la lectura."""

    semana = models.DateField(unique=True, help_text="Lunes de la semana a la que corresponde")
    titulo = models.CharField(max_length=200)
    pdf_adultos = models.FileField(upload_to=_archivo_estudio, blank=True)
    pdf_ninos = models.FileField(upload_to=_archivo_estudio, blank=True)
    audio = models.FileField(upload_to=_archivo_estudio, blank=True)
    subido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-semana"]
        verbose_name = "estudio semanal"
        verbose_name_plural = "estudios semanales"

    def __str__(self):
        return f"{self.semana} · {self.titulo}"


class Reunion(models.Model):
    grupo = models.ForeignKey(Grupo, on_delete=models.CASCADE, related_name="reuniones")
    fecha = models.DateField(default=date.today)
    notas = models.TextField(blank=True)
    creada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha"]
        constraints = [models.UniqueConstraint(fields=["grupo", "fecha"], name="reunion_unica")]
        verbose_name_plural = "reuniones"

    def __str__(self):
        return f"{self.grupo} · {self.fecha}"


class Asistencia(models.Model):
    reunion = models.ForeignKey(Reunion, on_delete=models.CASCADE, related_name="asistencias")
    persona = models.ForeignKey(Persona, on_delete=models.PROTECT, related_name="asistencias")
    presente = models.BooleanField(default=False)
    registrada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    actualizada_en = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["reunion", "persona"], name="asistencia_unica")
        ]

    def __str__(self):
        return f"{self.persona} · {'presente' if self.presente else 'ausente'}"


class Ofrenda(models.Model):
    class Tipo(models.TextChoices):
        REGULAR = "regular", "Ofrenda regular"
        ESPECIAL = "especial", "Ofrenda especial"

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente de aval"
        AVALADA = "avalada", "Avalada"
        DIFERENCIA = "diferencia", "Con diferencia"

    reunion = models.ForeignKey(Reunion, on_delete=models.PROTECT, related_name="ofrendas")
    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.REGULAR)
    concepto = models.CharField(max_length=150, blank=True)
    monto = models.DecimalField("monto capturado", max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    capturada_por = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-reunion__fecha", "-creada_en"]
        constraints = [
            # Una ofrenda regular por reunión; las especiales se distinguen por concepto
            models.UniqueConstraint(
                fields=["reunion", "tipo", "concepto"], name="ofrenda_unica_por_concepto"
            )
        ]

    def __str__(self):
        return f"{self.reunion} · {self.get_tipo_display()} · {self.monto}"


class OfrendaMovimiento(models.Model):
    """Historial de captura, corrección y aval. Solo se agregan filas."""

    class Tipo(models.TextChoices):
        CAPTURA = "captura", "Captura"
        CORRECCION = "correccion", "Corrección"
        AVAL = "aval", "Aval"

    ofrenda = models.ForeignKey(Ofrenda, on_delete=models.CASCADE, related_name="movimientos")
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    monto_anterior = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    diferencia = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    motivo = models.CharField(max_length=300, blank=True)
    usuario = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["creado_en", "id"]

    def __str__(self):
        return f"{self.ofrenda_id} · {self.get_tipo_display()} · {self.monto}"
