from django.contrib import admin

from .models import Unidad, UnidadMiembro


@admin.register(Unidad)
class UnidadAdmin(admin.ModelAdmin):
    list_display = ("nombre", "activa")


@admin.register(UnidadMiembro)
class UnidadMiembroAdmin(admin.ModelAdmin):
    list_display = ("unidad", "persona", "rol", "activo")
