from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from patients.models import Appointment
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Cancel appointments that are 3 or more days overdue'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=3,
            help='Number of days past appointment date to consider overdue (default: 3)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cancelled without actually cancelling'
        )

    def handle(self, *args, **options):
        days_overdue = options['days']
        dry_run = options['dry_run']
        
        today = timezone.now().date()
        cutoff_date = today - timedelta(days=days_overdue)
        
        # Find appointments that are overdue
        overdue_appointments = Appointment.objects.filter(
            appointment_date__lt=cutoff_date,
            status__in=['PENDING', 'CONFIRMED']
        ).select_related('patient')
        
        count = overdue_appointments.count()
        
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS('No overdue appointments found.')
            )
            return
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'DRY RUN: Would cancel {count} overdue appointment(s):'
                )
            )
            for appointment in overdue_appointments:
                days_past = (today - appointment.appointment_date).days
                self.stdout.write(
                    f'  - Appointment #{appointment.id}: '
                    f'{appointment.patient.first_name} {appointment.patient.last_name} - '
                    f'{appointment.procedure_type} on {appointment.appointment_date} '
                    f'({days_past} days overdue, status: {appointment.status})'
                )
        else:
            cancelled_count = 0
            for appointment in overdue_appointments:
                days_past = (today - appointment.appointment_date).days
                old_status = appointment.status
                appointment.status = 'CANCELLED'
                appointment.save(update_fields=['status', 'updated_at'])
                cancelled_count += 1
                
                logger.info(
                    f"Cancelled overdue appointment {appointment.id} "
                    f"(Patient: {appointment.patient}, Date: {appointment.appointment_date}, "
                    f"{days_past} days overdue, Previous status: {old_status})"
                )
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Cancelled appointment #{appointment.id}: '
                        f'{appointment.patient.first_name} {appointment.patient.last_name} - '
                        f'{appointment.procedure_type} on {appointment.appointment_date} '
                        f'({days_past} days overdue)'
                    )
                )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nSuccessfully cancelled {cancelled_count} overdue appointment(s).'
                )
            )


