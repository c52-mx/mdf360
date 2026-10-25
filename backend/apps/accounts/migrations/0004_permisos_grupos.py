from django.db import migrations

# Permisos nuevos del módulo Grupos (M3 / M1-08) para los roles ya sembrados.
NUEVOS = {
    "pastor": ["grupos.ver_todos", "grupos.gestionar", "grupos.material"],
    "anciano": ["grupos.ver_todos", "grupos.material"],
}


def agregar(apps, schema_editor):
    Rol = apps.get_model("accounts", "Rol")
    for clave, permisos in NUEVOS.items():
        rol = Rol.objects.filter(clave=clave).first()
        if rol:
            rol.permisos = sorted(set(rol.permisos) | set(permisos))
            rol.save(update_fields=["permisos"])


class Migration(migrations.Migration):
    dependencies = [("accounts", "0003_roles")]
    operations = [migrations.RunPython(agregar, migrations.RunPython.noop)]
