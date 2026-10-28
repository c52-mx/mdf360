from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("personas", "0003_unaccent"),
    ]

    operations = [
        migrations.AddField(
            model_name="personamovimiento",
            name="iglesia_destino",
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AlterField(
            model_name="personamovimiento",
            name="tipo",
            field=models.CharField(
                choices=[
                    ("alta", "Alta"),
                    ("cambio_nivel", "Cambio de nivel de registro"),
                    ("baja", "Baja"),
                    ("reactivacion", "Reactivación"),
                    ("traslado", "Traslado a otra iglesia"),
                    ("otro", "Otro"),
                ],
                max_length=20,
            ),
        ),
    ]
