from django.conf import settings
from django.db import models


class Publicacion(models.Model):
    """Algo que se publica para una o varias audiencias (la iglesia, un segmento, un grupo…)."""

    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    autor_nombre = models.CharField(max_length=150)  # se conserva aunque cambie la cuenta
    texto = models.TextField(max_length=2000)
    eliminada = models.BooleanField(default=False)
    creada_en = models.DateTimeField(auto_now_add=True, db_index=True)
    editada_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-creada_en", "-id"]

    def __str__(self):
        return f"{self.autor_nombre}: {self.texto[:40]}"


class Audiencia(models.Model):
    """A quién se dirige una publicación. Una publicación puede tener varias."""

    class Tipo(models.TextChoices):
        IGLESIA = "iglesia", "Toda la iglesia"
        SEGMENTO = "segmento", "Segmento"
        GRUPO = "grupo", "Grupo de Conexión"
        UNIDAD = "unidad", "Ministerio"

    publicacion = models.ForeignKey(
        Publicacion, on_delete=models.CASCADE, related_name="audiencias"
    )
    tipo = models.CharField(max_length=12, choices=Tipo.choices)
    ref_id = models.PositiveIntegerField()  # iglesia = 1; segmento = ver segmentos.py
    etiqueta = models.CharField(max_length=250)  # texto fijo con el que se publicó

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["publicacion", "tipo", "ref_id"], name="muro_audiencia_unica"
            )
        ]
        indexes = [models.Index(fields=["tipo", "ref_id"], name="muro_audiencia_idx")]

    def __str__(self):
        return self.etiqueta


class Reaccion(models.Model):
    """Una reacción por persona y publicación; reaccionar de nuevo cambia o quita la anterior."""

    class Tipo(models.TextChoices):
        ME_GUSTA = "me_gusta", "Me gusta"
        AMEN = "amen", "Amén"
        CORAZON = "corazon", "Me encanta"

    publicacion = models.ForeignKey(
        Publicacion, on_delete=models.CASCADE, related_name="reacciones"
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+"
    )
    tipo = models.CharField(max_length=12, choices=Tipo.choices)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["publicacion", "usuario"], name="muro_reaccion_unica")
        ]

    def __str__(self):
        return f"{self.usuario_id} {self.tipo} → {self.publicacion_id}"


class Comentario(models.Model):
    publicacion = models.ForeignKey(
        Publicacion, on_delete=models.CASCADE, related_name="comentarios"
    )
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    autor_nombre = models.CharField(max_length=150)
    texto = models.TextField(max_length=500)
    eliminado = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["creado_en", "id"]

    def __str__(self):
        return f"{self.autor_nombre}: {self.texto[:40]}"
