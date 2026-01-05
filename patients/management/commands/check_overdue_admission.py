from django.core.management.base import BaseCommand
from django.utils import timezone
from patients.models import Admission

class Command(BaseCommand):
    help = 'Auto-discharge patients whose expected discharge date has passed'

    def handle(self, *args, **kwargs):
        overdue_admissions = Admission.objects.filter(
            is_active=True,
            expected_discharge_date__lt=timezone.now()
        )
        
        count = 0
        for admission in overdue_admissions:
            admission.actual_discharge_date = admission.expected_discharge_date
            admission.discharge_notes = "Auto-discharged: Expected discharge date reached."
            admission.is_active = False
            admission.save()
            
            admission.patient.patient_status = 'OUT'
            admission.patient.save(update_fields=['patient_status'])
            count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Successfully auto-discharged {count} patients'))