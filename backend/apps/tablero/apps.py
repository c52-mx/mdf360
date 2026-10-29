from django.apps import AppConfig


class TableroConfig(AppConfig):
    name = "apps.tablero"
    label = "tablero"
    verbose_name = "Tablero de mensajes"

    def ready(self):
        from .origenes import registrar_origenes

        registrar_origenes()
