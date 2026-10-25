from django.apps import AppConfig


class GruposConfig(AppConfig):
    name = "apps.grupos"
    label = "grupos"
    verbose_name = "Grupos de Conexión"

    def ready(self):
        from .origen_peticiones import registrar_origen

        registrar_origen()

        from .origen_tablero import registrar_origen as registrar_tablero

        registrar_tablero()
