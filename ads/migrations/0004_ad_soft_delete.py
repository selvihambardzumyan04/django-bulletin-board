import django.db.models.manager
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ads", "0003_alter_ad_status"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="ad",
            options={
                "default_manager_name": "available_objects",
                "ordering": ["-created"],
            },
        ),
        migrations.AlterModelManagers(
            name="ad",
            managers=[
                ("available_objects", django.db.models.manager.Manager()),
            ],
        ),
        migrations.AddField(
            model_name="ad",
            name="is_removed",
            field=models.BooleanField(default=False),
        ),
    ]
