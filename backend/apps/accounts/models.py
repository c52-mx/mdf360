from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone

from .phone import normalize_whatsapp


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create(self, whatsapp, pin, **extra):
        user = self.model(whatsapp=normalize_whatsapp(whatsapp), **extra)
        if pin:
            user.set_password(pin)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(self, whatsapp, pin=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create(whatsapp, pin, **extra)

    def create_superuser(self, whatsapp, pin=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self._create(whatsapp, pin, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    """Usuario del sistema. Se identifica por su número de WhatsApp y entra con un PIN (M1-17)."""

    whatsapp = models.CharField("WhatsApp", max_length=16, unique=True)
    nombre = models.CharField(max_length=150)
    is_active = models.BooleanField("activo", default=True)
    is_staff = models.BooleanField("acceso al panel técnico", default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "whatsapp"
    REQUIRED_FIELDS = ["nombre"]

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"

    def __str__(self):
        return f"{self.nombre} ({self.whatsapp})"
