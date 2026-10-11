from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import AsignacionRol, Rol, User
from apps.accounts.phone import normalize_whatsapp


class Command(BaseCommand):
    help = "Asigna un rol a un usuario por consola (arranque inicial; no aplica la jerarquía)."

    def add_arguments(self, parser):
        parser.add_argument("whatsapp")
        parser.add_argument("roles", nargs="+", help="Claves: pastor, admin_tecnico, lider...")

    def handle(self, *args, whatsapp, roles, **options):
        user = User.objects.filter(whatsapp=normalize_whatsapp(whatsapp)).first()
        if not user:
            raise CommandError("No existe ese usuario.")
        for clave in roles:
            rol = Rol.objects.filter(clave=clave).first()
            if not rol:
                raise CommandError(f"No existe el rol «{clave}».")
            AsignacionRol.objects.get_or_create(usuario=user, rol=rol)
            if rol.exige_credencial_fuerte and not user.requires_strong_credential:
                user.requires_strong_credential = True
                user.save(update_fields=["requires_strong_credential"])
        self.stdout.write(f"{user}: {', '.join(user.roles_clave())}")
