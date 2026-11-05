import secrets

from django.db import migrations


def sembrar(apps, schema_editor):
    """Cada grupo activo tiene su enlace (y QR) fijo; los que no lo tenían lo reciben."""
    Grupo = apps.get_model("grupos", "Grupo")
    for grupo in Grupo.objects.filter(activo=True, enlace_token__isnull=True):
        grupo.enlace_token = secrets.token_urlsafe(18)
        grupo.save(update_fields=["enlace_token"])


class Migration(migrations.Migration):
    dependencies = [("grupos", "0013_sembrar_tipos_de_ofrenda")]
    operations = [migrations.RunPython(sembrar, migrations.RunPython.noop)]
