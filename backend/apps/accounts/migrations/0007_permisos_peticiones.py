from django.db import migrations

NUEVOS = {
    "pastor": ["peticiones.ver_todas", "peticiones.configurar"],
    "anciano": ["peticiones.ver_todas"],
    "admin_tecnico": ["peticiones.configurar"],  # edita la estructura del formulario, nunca el contenido
}


def agregar(apps, schema_editor):
    Rol = apps.get_model("accounts", "Rol")
    for clave, permisos in NUEVOS.items():
        rol = Rol.objects.filter(clave=clave).first()
        if rol:
            rol.permisos = sorted(set(rol.permisos) | set(permisos))
            rol.save(update_fields=["permisos"])


class Migration(migrations.Migration):
    dependencies = [("accounts", "0006_permiso_config")]
    operations = [migrations.RunPython(agregar, migrations.RunPython.noop)]
