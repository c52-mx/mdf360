import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

from apps.accounts.roles import ROLES


def sembrar(apps, schema_editor):
    Rol = apps.get_model("accounts", "Rol")
    for clave, (nombre, nivel, fuerte, permisos) in ROLES.items():
        Rol.objects.get_or_create(
            clave=clave,
            defaults={
                "nombre": nombre,
                "nivel": nivel,
                "exige_credencial_fuerte": fuerte,
                "permisos": permisos,
            },
        )


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_acceso_m1_17")]

    operations = [
        migrations.CreateModel(
            name="Rol",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("clave", models.SlugField(max_length=40, unique=True)),
                ("nombre", models.CharField(max_length=80)),
                ("nivel", models.PositiveSmallIntegerField(help_text="0 es el nivel más alto de la jerarquía")),
                ("exige_credencial_fuerte", models.BooleanField(default=False)),
                ("permisos", models.JSONField(default=list)),
                ("activo", models.BooleanField(default=True)),
            ],
            options={"verbose_name_plural": "roles", "ordering": ["nivel", "nombre"]},
        ),
        migrations.CreateModel(
            name="AsignacionRol",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                ("asignado_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("rol", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="asignaciones", to="accounts.rol")),
                ("usuario", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="asignaciones", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddConstraint(
            model_name="asignacionrol",
            constraint=models.UniqueConstraint(fields=("usuario", "rol"), name="asignacion_rol_unica"),
        ),
        migrations.RunPython(sembrar, migrations.RunPython.noop),
    ]
