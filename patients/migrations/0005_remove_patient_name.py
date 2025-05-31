# Generated manually

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0004_auto_20250531_1643'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='patient',
            name='name',
        ),
    ] 