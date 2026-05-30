from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("public_api", "0006_conference_conference_id_26d896_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="paper",
            name="embedded_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
