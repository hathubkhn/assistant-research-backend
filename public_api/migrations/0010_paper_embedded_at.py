from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("public_api", "0009_remove_conference_category_placeholder"),
    ]

    operations = [
        migrations.AddField(
            model_name="paper",
            name="embedded_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
