import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

CAMPOS_INICIALES = [
    {"clave": "peticion", "etiqueta": "Petición", "tipo": "textarea", "requerido": True, "activo": True, "opciones": []},
    {"clave": "solicitante", "etiqueta": "¿Quién la pide? (opcional)", "tipo": "texto", "requerido": False, "activo": True, "opciones": []},
    {
        "clave": "categoria",
        "etiqueta": "Categoría",
        "tipo": "seleccion",
        "requerido": False,
        "activo": True,
        "opciones": ["Salud", "Familia", "Trabajo", "Espiritual", "Otra"],
    },
]


def sembrar(apps, schema_editor):
    Formulario = apps.get_model("peticiones", "FormularioPeticion")
    Formulario.objects.get_or_create(version=1, defaults={"campos": CAMPOS_INICIALES})


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="FormularioPeticion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("version", models.PositiveIntegerField(unique=True)),
                ("campos", models.JSONField(default=list)),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                ("creado_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "formulario de peticiones", "verbose_name_plural": "formularios de peticiones", "ordering": ["-version"]},
        ),
        migrations.CreateModel(
            name="Peticion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("origen_tipo", models.CharField(db_index=True, max_length=40)),
                ("origen_id", models.PositiveIntegerField()),
                ("origen_etiqueta", models.CharField(max_length=250)),
                ("referencia_id", models.PositiveIntegerField(blank=True, null=True)),
                ("formulario_version", models.PositiveIntegerField()),
                ("datos_cifrados", models.TextField()),
                ("estado", models.CharField(choices=[("activa", "Activa"), ("atendida", "Atendida")], default="activa", max_length=20)),
                ("creada_en", models.DateTimeField(auto_now_add=True)),
                ("expira_en", models.DateTimeField(db_index=True)),
                ("atendida_en", models.DateTimeField(blank=True, null=True)),
                ("atendida_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("creada_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-creada_en"]},
        ),
        migrations.AddIndex(
            model_name="peticion",
            index=models.Index(fields=["origen_tipo", "origen_id"], name="peticiones_origen_idx"),
        ),
        migrations.RunPython(sembrar, migrations.RunPython.noop),
    ]
