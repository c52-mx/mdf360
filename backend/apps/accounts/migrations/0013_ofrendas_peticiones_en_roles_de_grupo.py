from django.db import migrations

# Lo que cada rol base del grupo ya podía hacer con ofrendas y peticiones cuando las reglas
# estaban fijas en el código; ahora son permisos del rol y se pueden ajustar.
NUEVOS = {
    "lider": [
        "ofrendas_ver",
        "ofrendas_capturar_suplente",
        "ofrendas_avalar_suplente",
        "peticiones_registrar",
        "peticiones_ver",
    ],
    "respaldo": [
        "ofrendas_ver",
        "ofrendas_capturar_suplente",
        "ofrendas_avalar_suplente",
        "peticiones_registrar",
        "peticiones_ver",
    ],
    "supervisor": ["ofrendas_ver", "peticiones_ver"],
    "secretario": ["ofrendas_capturar", "peticiones_registrar"],
    "tesorero": ["ofrendas_ver", "ofrendas_avalar"],
}


def agregar(apps, schema_editor):
    RolEquipo = apps.get_model("accounts", "RolEquipo")
    for clave, permisos in NUEVOS.items():
        for rol in RolEquipo.objects.filter(ambito="grupo", clave=clave):
            rol.permisos = sorted({*rol.permisos, *permisos})
            rol.save(update_fields=["permisos"])


class Migration(migrations.Migration):
    dependencies = [("accounts", "0012_permiso_formularios")]
    operations = [migrations.RunPython(agregar, migrations.RunPython.noop)]
