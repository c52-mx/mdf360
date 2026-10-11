from django.contrib.postgres.operations import UnaccentExtension
from django.db import migrations


class Migration(migrations.Migration):
    """Búsqueda de personas sin importar acentos (María = Maria)."""

    dependencies = [("personas", "0002_procesos_radiografia")]
    operations = [UnaccentExtension()]
