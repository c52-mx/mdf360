from django.db import migrations

# Los avisos publicados de toda la iglesia, de grupos y de ministerios pasan al muro como
# publicaciones con una sola audiencia. Los avisos personales («persona») no: son privados.
# Es una copia: el tablero actual sigue funcionando hasta que el muro lo sustituya.
TIPOS = {"iglesia": "iglesia", "grupo": "grupo", "unidad": "unidad"}


def copiar(apps, schema_editor):
    Mensaje = apps.get_model("tablero", "Mensaje")
    Publicacion = apps.get_model("muro", "Publicacion")
    Audiencia = apps.get_model("muro", "Audiencia")
    avisos = Mensaje.objects.filter(
        origen_tipo__in=TIPOS, estado="publicado", eliminado=False
    ).order_by("creado_en", "id")
    for m in avisos:
        p = Publicacion.objects.create(
            autor_id=m.autor_id, autor_nombre=m.autor_nombre, texto=m.texto
        )
        Publicacion.objects.filter(pk=p.pk).update(creada_en=m.creado_en)  # conserva la fecha
        Audiencia.objects.create(
            publicacion=p,
            tipo=TIPOS[m.origen_tipo],
            ref_id=m.origen_id,
            etiqueta=m.origen_etiqueta,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("muro", "0001_initial"),
        ("tablero", "0002_aviso_por_autorizar"),
    ]
    operations = [migrations.RunPython(copiar, migrations.RunPython.noop)]
