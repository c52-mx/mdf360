import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("grupos", "0006_retirado_por_baja"),
    ]

    operations = [
        migrations.AddField(
            model_name="grupo",
            name="enlace_token",
            field=models.CharField(blank=True, max_length=64, null=True, unique=True),
        ),
        migrations.CreateModel(
            name="SolicitudIngreso",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("nombre", models.CharField(max_length=100)),
                ("whatsapp", models.CharField(max_length=20)),
                ("acepta_datos", models.BooleanField(default=False)),
                (
                    "estado",
                    models.CharField(
                        choices=[
                            ("pendiente", "Pendiente"),
                            ("aprobada", "Aprobada"),
                            ("rechazada", "Rechazada"),
                        ],
                        default="pendiente",
                        max_length=12,
                    ),
                ),
                ("codigo", models.CharField(max_length=64, unique=True)),
                ("creada_en", models.DateTimeField(auto_now_add=True)),
                ("resuelta_en", models.DateTimeField(blank=True, null=True)),
                (
                    "grupo",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="solicitudes",
                        to="grupos.grupo",
                    ),
                ),
                (
                    "resuelta_por",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "solicitudes de ingreso",
                "ordering": ["creada_en"],
                "constraints": [
                    models.UniqueConstraint(
                        condition=models.Q(("estado", "pendiente")),
                        fields=("grupo", "whatsapp"),
                        name="solicitud_pendiente_unica",
                    )
                ],
            },
        ),
    ]
