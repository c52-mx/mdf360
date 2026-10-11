from django.contrib import admin

from .models import AsignacionRol, Rol, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("nombre", "whatsapp", "email", "is_active", "is_staff", "activated_at")
    search_fields = ("nombre", "whatsapp", "email")
    exclude = ("password",)
    readonly_fields = ("failed_attempts", "locked_until", "activated_at", "last_login")


@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ("nombre", "clave", "nivel", "exige_credencial_fuerte", "activo")


admin.site.register(AsignacionRol)
