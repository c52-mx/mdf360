from django.db import migrations, models

BASE = [
    "admin_tecnico",
    "pastor",
    "anciano",
    "supervisor",
    "lider",
    "secretario",
    "tesorero",
    "servidor",
    "miembro",
    "equipo_oracion",
]


def preparar(apps, schema_editor):
    Rol = apps.get_model("accounts", "Rol")
    for clave in ("admin_tecnico", "pastor"):
        rol = Rol.objects.filter(clave=clave).first()
        if rol:
            rol.permisos = sorted(set(rol.permisos) | {"roles.administrar"})
            rol.save(update_fields=["permisos"])
    pastor = Rol.objects.filter(clave="pastor").first()
    if pastor is not None:
        Rol.objects.get_or_create(
            clave="secretaria",
            defaults={
                "nombre": "Secretaria",
                "nivel": pastor.nivel,
                "exige_credencial_fuerte": True,
                "permisos": list(pastor.permisos),
            },
        )
    Rol.objects.filter(clave__in=BASE + ["secretaria"]).update(es_base=True)


class Migration(migrations.Migration):
    dependencies = [("accounts", "0008_rol_equipo_oracion")]

    operations = [
        migrations.AddField(
            model_name="rol",
            name="descripcion",
            field=models.CharField(blank=True, max_length=300),
        ),
        migrations.AddField(
            model_name="rol",
            name="es_base",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(preparar, migrations.RunPython.noop),
    ]
