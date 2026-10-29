from django.db import migrations

PERMISO = "formularios.gestionar"
ROLES = ["admin_tecnico", "pastor", "secretaria"]


def agregar(apps, schema_editor):
    Rol = apps.get_model("accounts", "Rol")
    for rol in Rol.objects.filter(clave__in=ROLES):
        if PERMISO not in rol.permisos:
            rol.permisos = sorted({*rol.permisos, PERMISO})
            rol.save(update_fields=["permisos"])


class Migration(migrations.Migration):
    dependencies = [("accounts", "0011_roles_de_equipo")]
    operations = [migrations.RunPython(agregar, migrations.RunPython.noop)]
