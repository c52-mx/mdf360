from django.contrib import admin

from .models import Formulario


@admin.register(Formulario)
class FormularioAdmin(admin.ModelAdmin):
    list_display = ("entidad", "version", "creado_en")
