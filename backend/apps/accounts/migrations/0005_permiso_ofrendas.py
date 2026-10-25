from django.db import migrations


def agregar(apps, schema_editor):
    Rol = apps.get_model("accounts", "Rol")
    rol = Rol.objects.filter(clave="pastor").first()
    if rol:
        rol.permisos = sorted(set(rol.permisos) | {"ofrendas.ver_todas"})
        rol.save(update_fields=["permisos"])


class Migration(migrations.Migration):
    dependencies = [("accounts", "0004_permisos_grupos")]
    operations = [migrations.RunPython(agregar, migrations.RunPython.noop)]
