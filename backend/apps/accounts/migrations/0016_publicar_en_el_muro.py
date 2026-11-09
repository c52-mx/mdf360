from django.db import migrations

# El Pastor y la Secretaria publican en el muro de toda la iglesia y por segmentos.
# Publicar en el grupo ya no viene de fábrica para el Asistente ni el Servidor: quien publica es
# un rol autorizado (el permiso sigue siendo configurable en cada rol de equipo).
PUBLICAN_MURO = ["pastor", "secretaria"]


def aplicar(apps, schema_editor):
    Rol = apps.get_model("accounts", "Rol")
    for rol in Rol.objects.filter(clave__in=PUBLICAN_MURO):
        rol.permisos = sorted({*rol.permisos, "muro.publicar"})
        rol.save(update_fields=["permisos"])
    RolEquipo = apps.get_model("accounts", "RolEquipo")
    for rol in RolEquipo.objects.filter(ambito="grupo", clave__in=["asistente", "servidor"]):
        if "avisos" in rol.permisos:
            rol.permisos = [p for p in rol.permisos if p != "avisos"]
            rol.save(update_fields=["permisos"])


class Migration(migrations.Migration):
    dependencies = [("accounts", "0015_permisos_ofrendas_iglesia")]
    operations = [migrations.RunPython(aplicar, migrations.RunPython.noop)]
