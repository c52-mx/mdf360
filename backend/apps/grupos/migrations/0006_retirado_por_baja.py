from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("grupos", "0005_sector_casa_suspension"),
    ]

    operations = [
        migrations.AddField(
            model_name="grupomiembro",
            name="retirado_por_baja",
            field=models.BooleanField(default=False),
        ),
    ]
