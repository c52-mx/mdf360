from django.apps import AppConfig


class UnidadesConfig(AppConfig):
    name = "apps.unidades"
    label = "unidades"
    verbose_name = "Unidades"

    def ready(self):
        from .origen_tablero import registrar_origen

        registrar_origen()
