import re

from django.db import migrations, models


def normalizar_sector(apps, schema_editor):
    """El sector pasa a ser una letra. Un texto libre anterior se conserva en la colonia."""
    Grupo = apps.get_model("grupos", "Grupo")
    for g in Grupo.objects.exclude(sector=""):
        valor = g.sector.strip()
        if re.fullmatch(r"[A-Za-z]", valor):
            g.sector = valor.upper()
        else:
            g.colonia = f"{g.colonia} ({valor})".strip() if g.colonia else valor
            g.sector = ""
        g.save(update_fields=["sector", "colonia"])


class Migration(migrations.Migration):
    dependencies = [
        ("grupos", "0004_alter_grupomiembro_desde_alter_reunion_fecha"),
    ]

    operations = [
        migrations.RunPython(normalizar_sector, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="grupo",
            name="sector",
            field=models.CharField(blank=True, max_length=1, verbose_name="sector (letra)"),
        ),
        migrations.AddField(
            model_name="grupo",
            name="casa",
            field=models.PositiveSmallIntegerField(
                blank=True, null=True, verbose_name="número de casa"
            ),
        ),
        migrations.AddField(
            model_name="grupo",
            name="suspendido",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="grupo",
            name="suspension_motivo",
            field=models.TextField(blank=True, verbose_name="motivo de la suspensión"),
        ),
        migrations.AddField(
            model_name="grupo",
            name="suspendido_en",
            field=models.DateField(blank=True, null=True),
        ),
    ]
