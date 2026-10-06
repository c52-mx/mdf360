from django.db import migrations

# Procesos de desarrollo discipular de la «Radiografía de miembros GC».
# (nombre, pide_maestro). El orden sigue la hoja: columna izquierda y luego la derecha.
PROCESOS = [
    ("Nacimiento Espiritual", False),
    ("Consolidación", False),
    ("Peniel", False),
    ("Bautismo en el Espíritu Santo", False),
    ("Bautismo en Agua", False),
    ("Sanidad Total", False),
    ("Fundamentos de la Vida Cristiana", True),
    ("Fundamentos Doctrinales", True),
    ("Fundamentos de Liderazgo", True),
    ("Avanzado hacia la Meta", True),
    ("Visión G. de Conexión", True),
    ("Espíritu Santo", True),
    ("Panorama Bíblico", True),
    ("Lanzamiento", False),
]


def sembrar(apps, schema_editor):
    Proceso = apps.get_model("personas", "ProcesoDiscipular")
    for orden, (nombre, pide_maestro) in enumerate(PROCESOS, start=1):
        Proceso.objects.get_or_create(
            nombre=nombre, defaults={"orden": orden, "pide_maestro": pide_maestro}
        )


class Migration(migrations.Migration):
    dependencies = [("personas", "0001_initial")]
    operations = [migrations.RunPython(sembrar, migrations.RunPython.noop)]
