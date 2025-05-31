# Generated manually

from django.db import migrations

def ensure_names(apps, schema_editor):
    Patient = apps.get_model('patients', 'Patient')
    for patient in Patient.objects.all():
        if not patient.first_name:
            patient.first_name = "Unknown"
        if not patient.last_name:
            patient.last_name = "Patient"
        patient.save()

class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0005_remove_patient_name'),
    ]

    operations = [
        migrations.RunPython(ensure_names),
    ] 