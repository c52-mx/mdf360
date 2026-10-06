from django.contrib import admin

from .models import Consentimiento, Persona, PersonaMovimiento, ProcesoDiscipular


@admin.register(Persona)
class PersonaAdmin(admin.ModelAdmin):
    list_display = ("nombre_completo", "nivel", "procedencia", "whatsapp", "activo")
    list_filter = ("nivel", "procedencia", "activo")
    search_fields = ("nombre", "apellido_paterno", "apellido_materno", "whatsapp", "email")


@admin.register(ProcesoDiscipular)
class ProcesoDiscipularAdmin(admin.ModelAdmin):
    list_display = ("nombre", "orden", "pide_maestro", "activo")
    list_editable = ("orden", "activo")


admin.site.register(Consentimiento)
admin.site.register(PersonaMovimiento)
