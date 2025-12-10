# yourapp/management/commands/generate_dummy_data.py
import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from patients.models import Patient, Appointment, UltrasoundExam
from billing.models import ServiceType, Bill, BillItem, Payment, Expense


class Command(BaseCommand):
    help = "Generate dummy data: 200 patients, 1 appointment each, 2 exams each, bills + payments"

    def handle(self, *args, **options):
        now = timezone.now()
        six_months_ago = now - timedelta(days=180)
        one_month_future = now + timedelta(days=30)

        # Load existing service types
        services = ServiceType.objects.all()
        if not services.exists():
            self.stdout.write(self.style.ERROR("No ServiceType objects found in the database!"))
            return

        self.stdout.write(f"Found {services.count()} ServiceType objects.")

        # Helper: random date in range
        def random_date():
            if random.random() < 0.7:
                return six_months_ago + timedelta(days=random.randint(0, 180))
            return now + timedelta(days=random.randint(1, 30))

        # Sample data pools
        first_names = ['Juan', 'Maria', 'Jose', 'Ana', 'Carlos', 'Luz', 'Pedro', 'Carmen', 'Miguel', 'Rosa', 'Elena', 'Rafael']
        last_names = ['Dela Cruz', 'Santos', 'Reyes', 'Garcia', 'Bautista', 'Fernandez', 'Cruz', 'Mendoza', 'Torres', 'Lim']
        genders = ['M', 'F']
        patient_types = ['REGULAR', 'SENIOR', 'PWD']
        reasons = ["Routine check-up", "Abdominal pain", "Pregnancy monitoring", "Pelvic pain", "Breast lump", "Thyroid swelling"]

        created = 0
        for i in range(200):
            fname = random.choice(first_names) + random.choice(['', ' Jr.', ' III', ''])
            lname = random.choice(last_names)

            patient = Patient.objects.create(
                first_name=fname,
                last_name=lname,
                sex=random.choice(genders),
                patient_type=random.choice(patient_types),
                birthday=timezone.now().date() - timedelta(days=random.randint(365*18, 365*80)),
                contact_number=f"09{random.randint(100000000, 999999999)}",
                email=f"{fname.lower()}.{lname.lower()}@example.com",
                region="NCR", province="Metro Manila", city="Quezon City", barangay="Diliman",
                street_address=f"Sample St. {random.randint(100, 999)}"
            )
            created += 1

            # 1 appointment
            app_date = random_date().date()
            app_time = timezone.datetime(2025, 1, 1, hour=random.randint(8, 17), minute=random.randint(0, 59)).time()

            appointment = Appointment.objects.create(
                patient=patient,
                procedure_type=random.choice(["Abdominal Ultrasound", "Pelvic Ultrasound", "Obstetric Ultrasound", "Transvaginal Ultrasound", "Breast Ultrasound", "Thyroid Ultrasound"]),
                appointment_date=app_date,
                appointment_time=app_time,
                reason=random.choice(reasons),
                status=random.choice(['PENDING', 'CONFIRMED', 'COMPLETED', 'CANCELLED'])
            )

            # 2 exams
            bill = None
            for _ in range(2):
                service = random.choice(services)
                exam = UltrasoundExam.objects.create(
                    patient=patient,
                    status='COMPLETED' if appointment.status == 'COMPLETED' else 'PENDING',
                    referring_physician=random.choice(["Dr. Smith", "Dr. Johnson", "Dr. Lee", "Dr. Garcia", "Dr. Reyes"]),
                    procedure_type=service,
                    exam_date=app_date,
                    exam_time=app_time,
                    findings="Normal findings." if random.random() > 0.4 else "Some abnormalities noted.",
                    impression="No significant abnormality." if random.random() > 0.5 else "Requires further evaluation.",
                    recommendations=random.choice(['NF', 'FU', 'RS', 'BI', 'FI']),
                )

                # Create or reuse bill
                if not bill:
                    bill, _ = Bill.objects.get_or_create(
                        patient=patient,
                        bill_date=app_date,
                        defaults={'subtotal': 0, 'discount': 0, 'tax': 0, 'total_amount': 0, 'status': 'PENDING'}
                    )

                # BillItem
                BillItem.objects.create(
                    bill=bill,
                    exam=exam,
                    service=service,
                    amount=service.base_price
                )

                # Recalculate totals
                bill.calculate_totals()

            # At least one payment per patient (70% chance of full payment, rest partial)
            if bill:
                total = bill.total_amount
                if random.random() < 0.7:
                    # Full payment
                    Payment.objects.create(
                        bill=bill,
                        amount=total,
                        payment_date=app_date,
                        payment_method=random.choice(['CASH', 'GCASH', 'BANK']),
                        created_by="Admin"
                    )
                else:
                    # Partial payment (30-90% of total)
                    paid = total * Decimal(random.uniform(0.3, 0.9))
                    Payment.objects.create(
                        bill=bill,
                        amount=paid,
                        payment_date=app_date,
                        payment_method=random.choice(['CASH', 'GCASH', 'BANK']),
                        created_by="Admin"
                    )
                # Update status after payment
                bill.update_status()

        # --- Add this block after the patient loop (before the final success message) ---

        # Generate some realistic expenses
        self.stdout.write("Generating dummy expenses...")

        expense_categories = [
            'UTILITIES', 'RENT', 'SALARY', 'EQUIPMENT', 'SUPPLIES',
            'MAINTENANCE', 'MARKETING', 'INSURANCE', 'OTHER'
        ]

        expense_descriptions = {
            'UTILITIES': ['Electricity bill', 'Water bill', 'Internet', 'Phone'],
            'RENT': ['Clinic rent - monthly'],
            'SALARY': ['Doctor salary', 'Technician salary', 'Receptionist salary', 'Janitor salary'],
            'EQUIPMENT': ['Ultrasound machine maintenance', 'Probe replacement', 'Printer ink'],
            'SUPPLIES': ['Gel bottles', 'Tissues', 'Gloves', 'Disinfectant'],
            'MAINTENANCE': ['Aircon cleaning', 'Building repair'],
            'MARKETING': ['Facebook ads', 'Flyers printing'],
            'INSURANCE': ['Clinic insurance', 'Liability insurance'],
            'OTHER': ['Office supplies', 'Refreshments', 'Miscellaneous']
        }

        start_date = timezone.now().date() - timedelta(days=365)  # last 12 months
        end_date = timezone.now().date()

        num_expenses = int(20)

        for _ in range(num_expenses):
            category = random.choice(expense_categories)
            description = random.choice(expense_descriptions[category])
            
            # Higher amounts for rent/salary, lower for supplies
            if category in ['RENT', 'SALARY']:
                amount = Decimal(random.randint(10000, 11000))
            elif category in ['EQUIPMENT', 'INSURANCE']:
                amount = Decimal(random.randint(5000, 10000))
            else:
                amount = Decimal(random.randint(500, 8000))
            
            # Random date in the past year
            days_back = random.randint(0, 365)
            expense_date = start_date + timedelta(days=days_back)
            
            Expense.objects.create(
                description=description,
                amount=amount,
                category=category,
                date=expense_date,
                notes=random.choice(["", "Paid via bank transfer", "Cash payment", "Monthly recurring"])
            )

        self.stdout.write(self.style.SUCCESS(f"Created {num_expenses} dummy expenses across the past year."))

        self.stdout.write(self.style.SUCCESS(f"Successfully created {created} patients, their appointments, exams, bills, and payments."))