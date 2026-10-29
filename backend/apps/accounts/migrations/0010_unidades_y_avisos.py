from django.db import migrations

NUEVOS = {
    "pastor": ["unidades.ver_todas", "unidades.gestionar", "avisos.iglesia", "avisos.personas"],
    "secretaria": ["unidades.ver_todas", "unidades.gestionar", "avisos.iglesia", "avisos.personas"],
    "anciano": ["unidades.ver_todas"],
}


def agregar(apps, schema_editor):
    Rol = apps.get_model("accounts", "Rol")
    for clave, permisos in NUEVOS.items():
        rol = Rol.objects.filter(clave=clave).first()
        if rol:
            rol.permisos = sorted(set(rol.permisos) | set(permisos))
            rol.save(update_fields=["permisos"])


class Migration(migrations.Migration):
    dependencies = [("accounts", "0009_administrador_de_roles")]
    operations = [migrations.RunPython(agregar, migrations.RunPython.noop)]
