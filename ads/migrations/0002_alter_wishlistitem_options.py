from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("ads", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="wishlistitem",
            options={"ordering": ["-added"]},
        ),
    ]
