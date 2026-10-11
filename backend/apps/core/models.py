from django.conf import settings
from django.db import models


class AppendOnlyError(Exception):
    """Se intentó modificar o borrar un registro que solo admite inserciones."""


class AppendOnlyQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise AppendOnlyError("La bitácora no se puede modificar.")

    def delete(self):
        raise AppendOnlyError("La bitácora no se puede borrar.")


class AuditEvent(models.Model):
    """Bitácora de auditoría de solo-añadir (NF-03).

    Bloqueado en la aplicación y en la base de datos (trigger de PostgreSQL, migración 0002).
    """

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    actor_repr = models.CharField(max_length=200, blank=True)
    action = models.CharField(max_length=60, db_index=True)
    target_type = models.CharField(max_length=60, blank=True)
    target_id = models.CharField(max_length=60, blank=True)
    detail = models.JSONField(default=dict, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "evento de bitácora"
        verbose_name_plural = "bitácora"

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} · {self.action}"

    def save(self, *args, **kwargs):
        if self.pk:
            raise AppendOnlyError("La bitácora no se puede modificar.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise AppendOnlyError("La bitácora no se puede borrar.")
