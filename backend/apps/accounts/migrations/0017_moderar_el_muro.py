from django.db import migrations

# El Pastor y la Secretaria moderan el muro (fijar, quitar y atender reportes).


def aplicar(apps, schema_editor):
    Rol = apps.get_model("accounts", "Rol")
    for rol in Rol.objects.filter(clave__in=["pastor", "secretaria"]):
        rol.permisos = sorted({*rol.permisos, "muro.moderar"})
        rol.save(update_fields=["permisos"])


class Migration(migrations.Migration):
    dependencies = [("accounts", "0016_publicar_en_el_muro")]
    operations = [migrations.RunPython(aplicar, migrations.RunPython.noop)]
