from datetime import timedelta

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone

from .credentials import validate_credential
from .phone import normalize_whatsapp


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create(self, whatsapp, pin, **extra):
        extra["email"] = (extra.get("email") or "").strip().lower()
        user = self.model(whatsapp=normalize_whatsapp(whatsapp), **extra)
        if pin:
            user.set_credential(pin)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    # `password` existe para que `createsuperuser` y los formularios de Django funcionen;
    # en este sistema la credencial es un PIN o una contraseña fuerte.
    def create_user(self, whatsapp, pin=None, password=None, **extra):
        pin = pin or password
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create(whatsapp, pin, **extra)

    def create_superuser(self, whatsapp, pin=None, password=None, **extra):
        pin = pin or password
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("requires_strong_credential", True)
        return self._create(whatsapp, pin, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    """Usuario del sistema (M1-17).

    La identidad estable es el `id`; el número de WhatsApp y el correo son datos de acceso
    y contacto que se pueden cambiar sin perder historial.
    """

    whatsapp = models.CharField("WhatsApp", max_length=16, unique=True)
    email = models.EmailField("correo", blank=True, default="")
    nombre = models.CharField(max_length=150)
    is_active = models.BooleanField("activo", default=True)
    is_staff = models.BooleanField("acceso al panel técnico", default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    requires_strong_credential = models.BooleanField(
        "exige contraseña fuerte",
        default=False,
        help_text="Roles sensibles (Pastor, Tesorero, Administrador): contraseña de 10+ caracteres",
    )
    activated_at = models.DateTimeField(null=True, blank=True)
    failed_attempts = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "whatsapp"
    REQUIRED_FIELDS = ["nombre"]

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        constraints = [
            models.UniqueConstraint(
                fields=["email"], condition=~models.Q(email=""), name="unique_email_when_present"
            )
        ]

    def __str__(self):
        return f"{self.nombre} ({self.whatsapp})"

    def save(self, *args, **kwargs):
        self.email = (self.email or "").strip().lower()
        super().save(*args, **kwargs)

    # --- credencial ---
    def set_credential(self, raw: str) -> None:
        """Valida y guarda el PIN (o contraseña fuerte). No persiste: el llamador hace save()."""
        validate_credential(raw, self.requires_strong_credential)
        self.set_password(raw)
        if self.activated_at is None:
            self.activated_at = timezone.now()
        self.failed_attempts = 0
        self.locked_until = None

    # --- bloqueo por intentos fallidos ---
    def is_locked(self) -> bool:
        return self.locked_until is not None and self.locked_until > timezone.now()

    def register_failure(self) -> None:
        self.failed_attempts += 1
        if self.failed_attempts >= settings.AUTH_LOCKOUT_ATTEMPTS:
            self.locked_until = timezone.now() + timedelta(minutes=settings.AUTH_LOCKOUT_MINUTES)
            self.failed_attempts = 0
        self.save(update_fields=["failed_attempts", "locked_until"])

    def clear_failures(self) -> None:
        if self.failed_attempts or self.locked_until:
            self.failed_attempts = 0
            self.locked_until = None
            self.save(update_fields=["failed_attempts", "locked_until"])


class ActivationToken(models.Model):
    """Enlace de un solo uso para activar una cuenta o reiniciar el acceso."""

    class Purpose(models.TextChoices):
        ACTIVATION = "activation", "Activación"
        RESET = "reset", "Reinicio de acceso"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tokens")
    token_hash = models.CharField(max_length=64, unique=True)
    purpose = models.CharField(max_length=20, choices=Purpose.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    def __str__(self):
        return f"{self.get_purpose_display()} · {self.user_id}"

    def is_valid(self) -> bool:
        return self.used_at is None and self.expires_at > timezone.now()
