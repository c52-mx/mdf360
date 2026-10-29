from django.apps import AppConfig


class PeticionesConfig(AppConfig):
    name = "apps.peticiones"
    label = "peticiones"
    verbose_name = "Peticiones de oración"

    def ready(self):
        from .origen_personal import registrar_origen

        registrar_origen()
