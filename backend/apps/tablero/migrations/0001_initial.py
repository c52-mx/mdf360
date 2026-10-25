import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="Mensaje",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("origen_tipo", models.CharField(db_index=True, max_length=40)),
                ("origen_id", models.PositiveIntegerField()),
                ("origen_etiqueta", models.CharField(max_length=250)),
                ("autor_nombre", models.CharField(max_length=150)),
                ("texto", models.TextField(max_length=1000)),
                ("fijado", models.BooleanField(default=False)),
                ("eliminado", models.BooleanField(default=False)),
                ("creado_en", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("autor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-fijado", "-creado_en"]},
        ),
        migrations.CreateModel(
            name="Lectura",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("origen_tipo", models.CharField(max_length=40)),
                ("origen_id", models.PositiveIntegerField()),
                ("visto_hasta", models.DateTimeField()),
                ("usuario", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="+", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddIndex(
            model_name="mensaje",
            index=models.Index(fields=["origen_tipo", "origen_id"], name="tablero_origen_idx"),
        ),
        migrations.AddConstraint(
            model_name="lectura",
            constraint=models.UniqueConstraint(fields=("usuario", "origen_tipo", "origen_id"), name="tablero_lectura_unica"),
        ),
    ]
