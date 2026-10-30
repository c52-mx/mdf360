from django.db import migrations

# La reunión del grupo es un evento fijo a la semana. A los grupos sin día se les pone el de su
# última reunión registrada (la hora que ya tenían se conserva). Los que nunca se reunieron y
# no tienen día quedan sin definir: la pantalla los obliga a completarlo al editarlos.


def poner_dia(apps, schema_editor):
    Grupo = apps.get_model("grupos", "Grupo")
    Reunion = apps.get_model("grupos", "Reunion")
    for grupo in Grupo.objects.filter(dia_semana__isnull=True):
        ultima = Reunion.objects.filter(grupo=grupo).order_by("-fecha").first()
        if ultima is not None:
            grupo.dia_semana = ultima.fecha.weekday()
            grupo.save(update_fields=["dia_semana"])


class Migration(migrations.Migration):
    dependencies = [("grupos", "0009_formularios")]
    operations = [migrations.RunPython(poner_dia, migrations.RunPython.noop)]
