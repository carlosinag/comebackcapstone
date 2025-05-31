from django.db import migrations, models
import django.db.models.deletion

def migrate_procedure_types(apps, schema_editor):
    UltrasoundExam = apps.get_model('patients', 'UltrasoundExam')
    ServiceType = apps.get_model('billing', 'ServiceType')
    
    # Map old values to existing ServiceType objects
    for exam in UltrasoundExam.objects.all():
        old_type = exam.procedure_type
        if old_type:
            # Try to find a matching service type
            service_type = ServiceType.objects.first()  # Get the first service type as default
            if service_type:
                exam.new_procedure_type = service_type
                exam.save()

class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0001_initial'),
        ('billing', '0001_initial'),
    ]

    operations = [
        # First create the new field
        migrations.AddField(
            model_name='ultrasoundexam',
            name='new_procedure_type',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='ultrasound_exams', to='billing.servicetype'),
        ),
        # Run the data migration
        migrations.RunPython(migrate_procedure_types),
        # Remove the old field
        migrations.RemoveField(
            model_name='ultrasoundexam',
            name='procedure_type',
        ),
        # Rename the new field to the original name
        migrations.RenameField(
            model_name='ultrasoundexam',
            old_name='new_procedure_type',
            new_name='procedure_type',
        ),
        # Make the field required (not null)
        migrations.AlterField(
            model_name='ultrasoundexam',
            name='procedure_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='ultrasound_exams', to='billing.servicetype'),
        ),
    ] 