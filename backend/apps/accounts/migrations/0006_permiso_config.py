from django.db import migrations

NUEVOS = {"pastor": ["config.gestionar"], "admin_tecnico": ["config.gestionar"]}


def agregar(apps, schema_editor):
    Rol = apps.get_model("accounts", "Rol")
    for clave, permisos in NUEVOS.items():
        rol = Rol.objects.filter(clave=clave).first()
        if rol:
            rol.permisos = sorted(set(rol.permisos) | set(permisos))
            rol.save(update_fields=["permisos"])


class Migration(migrations.Migration):
    dependencies = [("accounts", "0005_permiso_ofrendas")]
    operations = [migrations.RunPython(agregar, migrations.RunPython.noop)]
