import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [("personas", "0004_traslado")]

    operations = [
        migrations.CreateModel(
            name="Unidad",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("nombre", models.CharField(max_length=120, unique=True)),
                ("descripcion", models.CharField(blank=True, max_length=300)),
                ("activa", models.BooleanField(default=True)),
                ("creada_en", models.DateTimeField(auto_now_add=True)),
            ],
            options={"verbose_name_plural": "unidades", "ordering": ["nombre"]},
        ),
        migrations.CreateModel(
            name="UnidadMiembro",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "rol",
                    models.CharField(
                        choices=[
                            ("encargado", "Encargado"),
                            ("respaldo", "Respaldo"),
                            ("servidor", "Servidor"),
                        ],
                        default="servidor",
                        max_length=12,
                    ),
                ),
                ("activo", models.BooleanField(default=True)),
                ("desde", models.DateField(default=django.utils.timezone.localdate)),
                (
                    "persona",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="unidades",
                        to="personas.persona",
                    ),
                ),
                (
                    "unidad",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="miembros",
                        to="unidades.unidad",
                    ),
                ),
            ],
            options={
                "ordering": ["unidad", "rol", "persona__nombre"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("unidad", "persona", "rol"), name="unidad_miembro_unico"
                    )
                ],
            },
        ),
    ]
