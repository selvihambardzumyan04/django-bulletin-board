import django.db.models.deletion
from django.db import migrations, models

DEFAULT_CATEGORY = {"name": "General", "slug": "general", "status": "active"}


def add_default_category(apps, schema_editor):
    Category = apps.get_model("ads", "Category")
    Ad = apps.get_model("ads", "Ad")
    manager = Ad._default_manager
    if not manager.exists():
        return
    category, _ = Category.objects.get_or_create(
        slug=DEFAULT_CATEGORY["slug"],
        defaults={
            "name": DEFAULT_CATEGORY["name"],
            "status": DEFAULT_CATEGORY["status"],
        },
    )
    manager.filter(category__isnull=True).update(category=category)


class Migration(migrations.Migration):

    dependencies = [
        ("ads", "0004_ad_soft_delete"),
    ]

    operations = [
        migrations.CreateModel(
            name="Category",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        db_index=True, max_length=100, unique=True
                    ),
                ),
                ("slug", models.SlugField(max_length=100, unique=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Active"),
                            ("hidden", "Hidden"),
                        ],
                        default="active",
                        max_length=10,
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "categories",
                "ordering": ["name"],
            },
        ),
        migrations.AddField(
            model_name="ad",
            name="category",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="ads",
                to="ads.category",
            ),
        ),
        migrations.RunPython(
            add_default_category, migrations.RunPython.noop
        ),
        migrations.AlterField(
            model_name="ad",
            name="category",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="ads",
                to="ads.category",
            ),
        ),
    ]
