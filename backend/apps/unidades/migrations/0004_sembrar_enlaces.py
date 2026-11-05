import secrets

from django.db import migrations


def sembrar(apps, schema_editor):
    """Cada ministerio tiene su enlace (y QR) fijo desde que existe."""
    Unidad = apps.get_model("unidades", "Unidad")
    for unidad in Unidad.objects.filter(enlace_token__isnull=True):
        unidad.enlace_token = secrets.token_urlsafe(18)
        unidad.save(update_fields=["enlace_token"])


class Migration(migrations.Migration):
    dependencies = [("unidades", "0003_enlace_de_ministerio")]
    operations = [migrations.RunPython(sembrar, migrations.RunPython.noop)]
