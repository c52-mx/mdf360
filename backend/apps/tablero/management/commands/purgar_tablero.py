from django.core.management.base import BaseCommand

from apps.tablero import services


class Command(BaseCommand):
    help = "Borra los mensajes del tablero que superan los días de conservación."

    def handle(self, *args, **options):
        self.stdout.write(f"Mensajes borrados: {services.purgar_antiguos()}")
