from django.contrib import admin

from .models import FormularioPeticion


@admin.register(FormularioPeticion)
class FormularioPeticionAdmin(admin.ModelAdmin):
    list_display = ("version", "creado_en", "creado_por")
    readonly_fields = ("version", "campos", "creado_por", "creado_en")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# Peticion NO se registra a propósito: su contenido es confidencial y está cifrado; ni siquiera
# el panel de administración técnica debe poder listarlas.
