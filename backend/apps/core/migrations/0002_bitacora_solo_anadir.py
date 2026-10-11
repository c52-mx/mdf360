import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

# Refuerzo en la base de datos (NF-03): ningún usuario de la aplicación, ni siquiera con acceso
# directo, puede modificar o borrar eventos de bitácora. Solo se permite INSERT.
CREAR = """
CREATE OR REPLACE FUNCTION core_auditevent_inmutable() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'La bitácora es de solo-añadir: no se puede % registros.', lower(TG_OP);
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER core_auditevent_sin_cambios
BEFORE UPDATE OR DELETE ON core_auditevent
FOR EACH ROW EXECUTE FUNCTION core_auditevent_inmutable();

CREATE TRIGGER core_auditevent_sin_truncate
BEFORE TRUNCATE ON core_auditevent
FOR EACH STATEMENT EXECUTE FUNCTION core_auditevent_inmutable();
"""

QUITAR = """
DROP TRIGGER IF EXISTS core_auditevent_sin_truncate ON core_auditevent;
DROP TRIGGER IF EXISTS core_auditevent_sin_cambios ON core_auditevent;
DROP FUNCTION IF EXISTS core_auditevent_inmutable();
"""


class Migration(migrations.Migration):
    dependencies = [("core", "0001_acceso_m1_17")]

    operations = [
        # Con SET_NULL, borrar un usuario modificaría eventos y chocaría con el bloqueo.
        # Los usuarios no se borran (se desactivan) y el evento conserva `actor_repr`.
        migrations.AlterField(
            model_name="auditevent",
            name="actor",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunSQL(CREAR, QUITAR),
    ]
