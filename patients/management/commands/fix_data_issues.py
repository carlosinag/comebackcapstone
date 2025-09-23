from django.core.management.base import BaseCommand
from django.db import transaction
from patients.models import UltrasoundExam
from billing.models import Bill, BillItem, Payment
from decimal import Decimal
import random

class Command(BaseCommand):
    help = 'Fix data issues: update invalid recommendations and billing statuses'

    def handle(self, *args, **options):
        self.stdout.write('Fixing data issues...')
        
        # Fix invalid recommendation values
        self.fix_recommendations()
        
        # Update all billing statuses to PAID
        self.fix_billing_statuses()
        
        # Create payments for bills that don't have any
        self.create_missing_payments()
        
        self.stdout.write(
            self.style.SUCCESS('Successfully fixed all data issues!')
        )

    def fix_recommendations(self):
        """Fix invalid recommendation values"""
        self.stdout.write('Fixing invalid recommendation values...')
        
        # Valid recommendation choices
        valid_recommendations = ['FI', 'FU', 'RS', 'BI', 'NF']
        
        # Find exams with invalid recommendations
        invalid_exams = UltrasoundExam.objects.exclude(
            recommendations__in=valid_recommendations
        )
        
        updated_count = 0
        for exam in invalid_exams:
            exam.recommendations = random.choice(valid_recommendations)
            exam.save()
            updated_count += 1
        
        self.stdout.write(f'Updated {updated_count} exams with invalid recommendations')

    def fix_billing_statuses(self):
        """Update all billing statuses to PAID"""
        self.stdout.write('Updating all billing statuses to PAID...')
        
        # Update all bills to PAID status
        bills_updated = Bill.objects.filter(status__in=['PENDING', 'PARTIAL', 'CANCELLED']).update(status='PAID')
        
        self.stdout.write(f'Updated {bills_updated} bills to PAID status')

    def create_missing_payments(self):
        """Create payments for bills that don't have any payments"""
        self.stdout.write('Creating missing payments...')
        
        payment_methods = ['CASH', 'GCASH', 'BANK']
        
        # Find bills without payments
        bills_without_payments = Bill.objects.filter(payments__isnull=True)
        
        created_count = 0
        for bill in bills_without_payments:
            # Create a payment for the full amount
            Payment.objects.create(
                bill=bill,
                amount=bill.total_amount,
                payment_date=bill.bill_date,
                payment_method=random.choice(payment_methods),
                reference_number=f"REF{random.randint(100000, 999999)}" if random.choice(payment_methods) != 'CASH' else "",
                notes="Payment created during data fix",
                created_by="System"
            )
            created_count += 1
        
        self.stdout.write(f'Created {created_count} missing payments')
