from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ads", "0002_alter_wishlistitem_options"),
    ]

    operations = [
        migrations.AlterField(
            model_name="ad",
            name="status",
            field=models.CharField(
                choices=[
                    ("active", "Active"),
                    ("deactivated", "Deactivated"),
                    ("blocked", "Blocked"),
                ],
                default="active",
                max_length=12,
            ),
        ),
    ]
