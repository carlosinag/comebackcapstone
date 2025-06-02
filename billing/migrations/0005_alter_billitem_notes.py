# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0004_merge_20250602_1818'),
    ]

    operations = [
        migrations.AlterField(
            model_name='billitem',
            name='notes',
            field=models.TextField(blank=True, null=True),
        ),
    ] 