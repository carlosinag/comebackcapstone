from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from patients.models import Patient, UltrasoundExam, Appointment
from billing.models import Bill


class Command(BaseCommand):
    help = 'Merge duplicate patients, consolidate related records, and keep only 100 active patients.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--keep', type=int, default=100,
            help='Number of active patients to keep (default: 100)'
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Show what would change without modifying data'
        )
        parser.add_argument(
            '--hard-delete', action='store_true',
            help='Hard delete duplicates and extras instead of archiving them'
        )

    def handle(self, *args, **options):
        keep = options['keep']
        dry_run = options['dry_run']
        hard_delete = options['hard_delete']

        self.stdout.write(
            f"Starting dedupe and limit process (keep={keep}, dry_run={dry_run}, hard_delete={hard_delete})..."
        )

        with transaction.atomic():
            # Step 1: Merge duplicates by (first_name, last_name, contact_number)
            merged_pairs = self.merge_duplicates(dry_run=dry_run, hard_delete=hard_delete)
            self.stdout.write(f"Merged {len(merged_pairs)} duplicate patient groups.")

            # Step 2: Cap to N active patients by archiving oldest extras
            archived = self.cap_active_patients(keep=keep, dry_run=dry_run, hard_delete=hard_delete)
            action_word = 'Deleted' if hard_delete else 'Archived'
            self.stdout.write(f"{action_word} {archived} patient(s) to enforce cap of {keep} active patients.")

            if dry_run:
                transaction.set_rollback(True)
                self.stdout.write(self.style.WARNING('Dry run complete. No changes were committed.'))
            else:
                self.stdout.write(self.style.SUCCESS('Deduplication and capping completed successfully.'))

    def merge_duplicates(self, dry_run: bool = False, hard_delete: bool = False):
        """
        Merge patients that appear to be duplicates by exact match on
        first_name, last_name, and contact_number. The newest created
        record is treated as canonical; older ones are merged into it.
        Related records (exams, appointments, bills) are reassigned.
        Older patients are then hard-deleted if already archived or
        soft-archived otherwise.
        """
        key_to_patients = {}
        for patient in Patient.objects.all().only(
            'id', 'first_name', 'last_name', 'contact_number', 'created_at', 'is_archived'
        ):
            key = (
                (patient.first_name or '').strip().lower(),
                (patient.last_name or '').strip().lower(),
                (patient.contact_number or '').strip()
            )
            key_to_patients.setdefault(key, []).append(patient)

        merges = []
        for key, patients in key_to_patients.items():
            if not key[0] or not key[1] or not key[2]:
                # Skip groups with missing identifying info
                continue
            if len(patients) <= 1:
                continue

            # Choose canonical: most recent created_at
            patients_sorted = sorted(patients, key=lambda p: p.created_at or timezone.now(), reverse=True)
            canonical = patients_sorted[0]
            duplicates = patients_sorted[1:]

            for dup in duplicates:
                # Reassign related objects
                if not dry_run:
                    UltrasoundExam.objects.filter(patient=dup).update(patient=canonical)
                    Appointment.objects.filter(patient=dup).update(patient=canonical)
                    Bill.objects.filter(patient=dup).update(patient=canonical)

                    if hard_delete:
                        # Permanently remove the duplicate record
                        dup.hard_delete()
                    else:
                        # Soft-archive the duplicate
                        if not dup.is_archived:
                            dup.is_archived = True
                            dup.archived_at = timezone.now()
                            dup.save(update_fields=['is_archived', 'archived_at'])

                merges.append((dup.id, canonical.id))

        return merges

    def cap_active_patients(self, keep: int, dry_run: bool = False, hard_delete: bool = False) -> int:
        """
        Ensure only `keep` active patients remain by archiving the oldest extras
        based on `created_at` ascending (oldest first). Does not touch already
        archived patients.
        """
        active_qs = Patient.objects.filter(is_archived=False).order_by('-created_at').only('id', 'is_archived', 'archived_at', 'created_at')
        count_active = active_qs.count()
        if count_active <= keep:
            return 0

        # Determine which to archive: all after the first `keep` most recent
        ids_to_keep = list(active_qs.values_list('id', flat=True)[:keep])
        extras = Patient.objects.filter(is_archived=False).exclude(id__in=ids_to_keep).only('id')

        archived = 0
        if not dry_run:
            for p in extras:
                if hard_delete:
                    p.hard_delete()
                else:
                    p.is_archived = True
                    p.archived_at = timezone.now()
                    p.save(update_fields=['is_archived', 'archived_at'])
                archived += 1
        else:
            archived = extras.count()

        return archived


