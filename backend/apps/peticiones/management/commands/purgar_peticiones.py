from django.core.management.base import BaseCommand

from apps.peticiones import services


class Command(BaseCommand):
    help = "Borra las peticiones de oración cuyo plazo de conservación ya terminó."

    def handle(self, *args, **options):
        total = services.purgar_vencidas()
        self.stdout.write(f"Peticiones borradas: {total}")
