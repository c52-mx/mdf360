from django.db import migrations

# Un Asistente o Servidor no veía su propio grupo ni el estudio de la semana: sus roles no traían
# ningún permiso. Ahora pueden ver su grupo, el estudio y publicar en el tablero del grupo.
# Publicar ya no basta para moderar: fijar o quitar avisos ajenos pasa a ser un permiso aparte
# (avisos_moderar) que conservan todos los roles que hoy publican.
BASICO = ["avisos", "estudio", "ver"]


def aplicar(apps, schema_editor):
    RolEquipo = apps.get_model("accounts", "RolEquipo")
    # En una base nueva el Asistente y el Servidor ya traen «avisos»: ellos no moderan
    for rol in RolEquipo.objects.filter(ambito="grupo").exclude(clave__in=["asistente", "servidor"]):
        if "avisos" in rol.permisos:
            rol.permisos = sorted({*rol.permisos, "avisos_moderar"})
            rol.save(update_fields=["permisos"])
    for rol in RolEquipo.objects.filter(ambito="grupo", clave__in=["asistente", "servidor"]):
        rol.permisos = sorted({*rol.permisos, *BASICO})
        rol.save(update_fields=["permisos"])


class Migration(migrations.Migration):
    dependencies = [("accounts", "0013_ofrendas_peticiones_en_roles_de_grupo")]
    operations = [migrations.RunPython(aplicar, migrations.RunPython.noop)]
