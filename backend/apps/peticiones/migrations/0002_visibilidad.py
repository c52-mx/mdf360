from django.db import migrations, models


def marcar_identifica(apps, schema_editor):
    """El campo «solicitante» del formulario inicial identifica a la persona."""
    Formulario = apps.get_model("peticiones", "FormularioPeticion")
    for f in Formulario.objects.all():
        for c in f.campos:
            c.setdefault("identifica", c.get("clave") == "solicitante")
        f.save(update_fields=["campos"])


class Migration(migrations.Migration):
    dependencies = [("peticiones", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="peticion",
            name="visibilidad",
            field=models.CharField(
                choices=[("lideres", "Solo líderes"), ("grupo", "Mi grupo"), ("equipo", "Equipo de oración")],
                default="lideres",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="peticion",
            name="ocultar_nombre",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(marcar_identifica, migrations.RunPython.noop),
    ]
