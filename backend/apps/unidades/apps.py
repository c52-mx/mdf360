from django.apps import AppConfig


class UnidadesConfig(AppConfig):
    name = "apps.unidades"
    label = "unidades"
    verbose_name = "Ministerios"

    def ready(self):
        from .origen_tablero import registrar_origen

        registrar_origen()

        from .origen_peticiones import registrar_origen as registrar_peticiones

        registrar_peticiones()
