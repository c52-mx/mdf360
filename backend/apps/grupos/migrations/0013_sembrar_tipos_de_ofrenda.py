from django.db import migrations

# Lo que ya existía (regular y especial) pasa al catálogo; se suman los tipos de la iglesia.
TIPOS = [
    ("Ofrenda regular", True, True),
    ("Ofrenda especial", True, True),
    ("Diezmo", False, True),
    ("Primicia", False, True),
    ("Ofrenda misionera", False, True),
]


def sembrar(apps, schema_editor):
    Tipo = apps.get_model("grupos", "TipoOfrenda")
    Ofrenda = apps.get_model("grupos", "Ofrenda")
    for nombre, para_grupo, para_iglesia in TIPOS:
        Tipo.objects.get_or_create(
            nombre=nombre, defaults={"para_grupo": para_grupo, "para_iglesia": para_iglesia}
        )
    regular = Tipo.objects.get(nombre="Ofrenda regular")
    especial = Tipo.objects.get(nombre="Ofrenda especial")
    Ofrenda.objects.filter(tipo="regular", tipo_ofrenda__isnull=True).update(tipo_ofrenda=regular)
    Ofrenda.objects.filter(tipo="especial", tipo_ofrenda__isnull=True).update(tipo_ofrenda=especial)


class Migration(migrations.Migration):
    dependencies = [("grupos", "0012_catalogo_tipos_ofrenda_y_ofrenda_iglesia")]
    operations = [migrations.RunPython(sembrar, migrations.RunPython.noop)]
