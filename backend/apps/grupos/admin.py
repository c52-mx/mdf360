from django.contrib import admin

from .models import Asistencia, EstudioSemanal, Grupo, GrupoMiembro, Reunion


@admin.register(Grupo)
class GrupoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tipo", "sector", "dia_semana", "activo")
    list_filter = ("tipo", "activo")


admin.site.register(GrupoMiembro)
admin.site.register(EstudioSemanal)
admin.site.register(Reunion)
admin.site.register(Asistencia)
