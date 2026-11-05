from django.db import migrations

NUEVOS = ["ofrendas.iglesia_capturar", "ofrendas.iglesia_avalar", "ofrendas.catalogo"]
# El Tesorero (global) captura y avala las de la iglesia; Pastor y Secretaria lo administran todo.
POR_ROL = {
    "pastor": NUEVOS,
    "secretaria": NUEVOS,
    "tesorero": ["ofrendas.iglesia_capturar", "ofrendas.iglesia_avalar"],
}


def agregar(apps, schema_editor):
    Rol = apps.get_model("accounts", "Rol")
    for clave, permisos in POR_ROL.items():
        rol = Rol.objects.filter(clave=clave).first()
        if rol:
            rol.permisos = sorted(set(rol.permisos) | set(permisos))
            rol.save(update_fields=["permisos"])


class Migration(migrations.Migration):
    dependencies = [("accounts", "0014_basico_para_asistente_y_servidor")]
    operations = [migrations.RunPython(agregar, migrations.RunPython.noop)]
