from django.db import migrations


def crear(apps, schema_editor):
    Rol = apps.get_model("accounts", "Rol")
    Rol.objects.get_or_create(
        clave="equipo_oracion",
        defaults={
            "nombre": "Equipo de oración",
            "nivel": 8,
            "exige_credencial_fuerte": False,
            "permisos": ["peticiones.equipo_oracion"],
        },
    )


class Migration(migrations.Migration):
    dependencies = [("accounts", "0007_permisos_peticiones")]
    operations = [migrations.RunPython(crear, migrations.RunPython.noop)]
