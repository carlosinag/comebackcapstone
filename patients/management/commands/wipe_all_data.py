import os
import shutil

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.conf import settings

from patients.models import Patient, UltrasoundExam, UltrasoundImage, Appointment
from billing.models import Bill, BillItem, Payment


class Command(BaseCommand):
    help = 'PERMANENTLY delete all application data (patients, exams, appointments, bills, payments). Use with caution.'

    def add_arguments(self, parser):
        parser.add_argument('--yes', action='store_true', help='Confirm destructive action non-interactively')
        parser.add_argument('--delete-media', action='store_true', help='Also delete uploaded media files under MEDIA_ROOT')

    def handle(self, *args, **options):
        confirm = options['yes']
        delete_media = options['delete_media']

        if not confirm:
            raise CommandError('Refusing to proceed without --yes')

        self.stdout.write('Wiping ALL application data...')

        with transaction.atomic():
            # Delete billing first (payments -> bill items -> bills)
            deleted_payments, _ = Payment.objects.all().delete()
            deleted_bill_items, _ = BillItem.objects.all().delete()
            deleted_bills, _ = Bill.objects.all().delete()

            # Delete exam images first to remove files if storage is configured for delete
            deleted_images, _ = UltrasoundImage.objects.all().delete()

            # Delete patients domain data (appointments -> exams -> patients)
            deleted_appointments, _ = Appointment.objects.all().delete()
            deleted_exams, _ = UltrasoundExam.objects.all().delete()
            deleted_patients, _ = Patient.objects.all().delete()

        self.stdout.write(self.style.SUCCESS(
            f'Deletion complete. Removed: payments={deleted_payments}, bill_items={deleted_bill_items}, bills={deleted_bills}, images={deleted_images}, appointments={deleted_appointments}, exams={deleted_exams}, patients={deleted_patients}'
        ))

        if delete_media:
            media_root = getattr(settings, 'MEDIA_ROOT', None)
            if media_root and os.path.isdir(media_root):
                try:
                    shutil.rmtree(media_root)
                    os.makedirs(media_root, exist_ok=True)
                    self.stdout.write(self.style.WARNING('MEDIA_ROOT purged and recreated.'))
                except Exception as exc:
                    raise CommandError(f'Failed to delete MEDIA_ROOT: {exc}')
            else:
                self.stdout.write('MEDIA_ROOT not configured or not a directory; skipped media deletion.')


