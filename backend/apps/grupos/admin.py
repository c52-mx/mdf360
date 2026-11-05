from django.contrib import admin

from .models import (
    Asistencia,
    EstudioSemanal,
    Grupo,
    GrupoMiembro,
    Ofrenda,
    OfrendaIglesia,
    OfrendaIglesiaMovimiento,
    OfrendaMovimiento,
    Reunion,
    TipoOfrenda,
)


@admin.register(Grupo)
class GrupoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tipo", "sector", "dia_semana", "activo")
    list_filter = ("tipo", "activo")


admin.site.register(GrupoMiembro)
admin.site.register(EstudioSemanal)
admin.site.register(Reunion)
admin.site.register(Asistencia)
admin.site.register(Ofrenda)
admin.site.register(OfrendaMovimiento)
admin.site.register(OfrendaIglesia)
admin.site.register(OfrendaIglesiaMovimiento)
admin.site.register(TipoOfrenda)
