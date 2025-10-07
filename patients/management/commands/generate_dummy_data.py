from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta, date
import random
from decimal import Decimal

from patients.models import Patient, UltrasoundExam, Appointment
from billing.models import ServiceType, Bill, BillItem, Payment

class Command(BaseCommand):
    help = 'Generate comprehensive dummy data for the ultrasound clinic system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--patients',
            type=int,
            default=100,
            help='Number of patients to create (default: 100)'
        )

    def handle(self, *args, **options):
        num_patients = options['patients']
        
        self.stdout.write(f'Generating {num_patients} patients with comprehensive data...')
        
        # Ensure we have service types
        self.create_service_types()
        
        # Generate patients
        patients = self.create_patients(num_patients)
        
        # Generate ultrasound exams
        exams = self.create_ultrasound_exams(patients)
        
        # Generate appointments
        appointments = self.create_appointments(patients)
        
        # Generate bills and payments
        bills = self.create_bills_and_payments(exams)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created:\n'
                f'- {len(patients)} patients\n'
                f'- {len(exams)} ultrasound exams\n'
                f'- {len(appointments)} appointments\n'
                f'- {len(bills)} bills with payments'
            )
        )

    def create_service_types(self):
        """Ensure all service types exist"""
        services = [
            {'name': 'Abdominal Ultrasound', 'description': 'Complete examination of the abdominal organs', 'base_price': 2500.00},
            {'name': 'Breast Ultrasound', 'description': 'Bilateral breast examination', 'base_price': 2000.00},
            {'name': 'Thyroid Ultrasound', 'description': 'Examination of the thyroid gland', 'base_price': 1800.00},
            {'name': 'Pelvic Ultrasound', 'description': 'Examination of the pelvic organs', 'base_price': 2200.00},
            {'name': 'Obstetric Ultrasound', 'description': 'Pregnancy examination', 'base_price': 2500.00},
            {'name': 'Transvaginal Ultrasound', 'description': 'Internal pelvic examination', 'base_price': 2200.00},
            {'name': 'Scrotal Ultrasound', 'description': 'Testicular examination', 'base_price': 1800.00},
            {'name': 'Doppler Ultrasound', 'description': 'Blood flow examination', 'base_price': 3000.00},
        ]
        
        for service_data in services:
            ServiceType.objects.get_or_create(
                name=service_data['name'],
                defaults={
                    'description': service_data['description'],
                    'base_price': service_data['base_price'],
                    'is_active': True
                }
            )

    def create_patients(self, num_patients):
        """Create patients with realistic demographics"""
        first_names = [
            'Maria', 'Jose', 'Ana', 'Juan', 'Carmen', 'Pedro', 'Rosa', 'Antonio', 'Isabel', 'Francisco',
            'Teresa', 'Manuel', 'Dolores', 'Carlos', 'Pilar', 'Miguel', 'Concepcion', 'Rafael', 'Mercedes', 'Javier',
            'Cristina', 'Alejandro', 'Monica', 'Sergio', 'Patricia', 'David', 'Laura', 'Roberto', 'Elena', 'Fernando',
            'Beatriz', 'Alberto', 'Nuria', 'Santiago', 'Silvia', 'Diego', 'Raquel', 'Pablo', 'Cristina', 'Adrian',
            'Marta', 'Hector', 'Sandra', 'Ivan', 'Lorena', 'Oscar', 'Natalia', 'Ruben', 'Miriam', 'Gonzalo',
            'Claudia', 'Victor', 'Alicia', 'Mario', 'Sofia', 'Jorge', 'Paula', 'Alvaro', 'Celia', 'Nicolas',
            'Eva', 'Hugo', 'Rocio', 'Guillermo', 'Cristina', 'Marcos', 'Teresa', 'Joaquin', 'Pilar', 'Ramon',
            'Carmen', 'Sergio', 'Beatriz', 'Alfonso', 'Elena', 'Jose', 'Maria', 'Antonio', 'Isabel', 'Francisco'
        ]
        
        last_names = [
            'Garcia', 'Rodriguez', 'Gonzalez', 'Fernandez', 'Lopez', 'Martinez', 'Sanchez', 'Perez', 'Gomez', 'Martin',
            'Jimenez', 'Ruiz', 'Hernandez', 'Diaz', 'Moreno', 'Alvarez', 'Romero', 'Alonso', 'Gutierrez', 'Navarro',
            'Torres', 'Dominguez', 'Vazquez', 'Ramos', 'Gil', 'Ramirez', 'Serrano', 'Blanco', 'Suarez', 'Molina',
            'Morales', 'Ortega', 'Delgado', 'Castro', 'Ortiz', 'Rubio', 'Marin', 'Sanz', 'Iglesias', 'Medina',
            'Cortes', 'Castillo', 'Garrido', 'Santos', 'Lozano', 'Guerrero', 'Cano', 'Prieto', 'Mendez', 'Cruz'
        ]
        
        genders = ['M', 'F']
        patient_types = ['REGULAR', 'SENIOR', 'PWD']
        marital_statuses = ['S', 'M', 'W', 'D']
        regions = ['NCR', 'Region III', 'Region IV-A', 'Region VII']
        provinces = ['Metro Manila', 'Laguna', 'Cavite', 'Rizal', 'Bulacan', 'Cebu', 'Bohol']
        cities = ['Manila', 'Quezon City', 'Makati', 'Taguig', 'Pasig', 'Mandaluyong', 'San Juan', 'Marikina', 'Cebu City', 'Mandaue']
        barangays = ['Barangay 1', 'Barangay 2', 'Barangay 3', 'Barangay 4', 'Barangay 5', 'Poblacion', 'Centro', 'San Jose', 'San Pedro', 'Santa Maria']
        
        patients = []
        for i in range(num_patients):
            # Create realistic birth dates (ages 18-80)
            age = random.randint(18, 80)
            birth_year = timezone.now().year - age
            birth_month = random.randint(1, 12)
            birth_day = random.randint(1, 28)
            
            patient = Patient.objects.create(
                first_name=random.choice(first_names),
                last_name=random.choice(last_names),
                birthday=date(birth_year, birth_month, birth_day),
                sex=random.choice(genders),
                marital_status=random.choice(marital_statuses),
                contact_number=f"09{random.randint(10000000, 99999999)}",
                email=f"patient{i+1}@example.com",
                region=random.choice(regions),
                province=random.choice(provinces),
                city=random.choice(cities),
                barangay=random.choice(barangays),
                street_address=f"{random.randint(1, 999)} {random.choice(['Main St', 'Oak Ave', 'Pine St', 'Elm St', 'Maple Ave'])}",
                patient_type=random.choice(patient_types),
                id_number=f"ID{random.randint(100000, 999999)}" if random.choice(patient_types) in ['SENIOR', 'PWD'] else "",
                created_at=timezone.now() - timedelta(days=random.randint(1, 365))
            )
            patients.append(patient)
            
        return patients

    def create_ultrasound_exams(self, patients):
        """Create ultrasound exams with various procedure types"""
        service_types = list(ServiceType.objects.all())
        recommendations = ['FI', 'FU', 'RS', 'BI', 'NF']
        
        exams = []
        for patient in patients:
            # Each patient has 1-5 exams
            num_exams = random.randint(1, 5)
            
            for i in range(num_exams):
                exam_date = timezone.now().date() - timedelta(days=random.randint(1, 365))
                exam_time = datetime.combine(exam_date, datetime.min.time().replace(
                    hour=random.randint(8, 17),
                    minute=random.choice([0, 15, 30, 45])
                )).time()
                
                exam = UltrasoundExam.objects.create(
                    patient=patient,
                    procedure_type=random.choice(service_types),
                    exam_date=exam_date,
                    exam_time=exam_time,
                    findings=f"Findings for {patient.first_name} {patient.last_name} - Exam {i+1}",
                    recommendations=random.choice(recommendations),
                    notes=f"Additional notes for exam {i+1}",
                    created_at=timezone.now() - timedelta(days=random.randint(1, 365))
                )
                exams.append(exam)
                
        return exams

    def create_appointments(self, patients):
        """Create appointments for patients"""
        procedure_choices = ['ABD', 'PEL', 'OBS', 'TVS', 'BRE', 'THY', 'SCR', 'DOP', 'OTH']
        statuses = ['PENDING', 'CONFIRMED', 'CANCELLED', 'COMPLETED']
        
        appointments = []
        for patient in patients:
            # 30% chance of having appointments
            if random.random() < 0.3:
                num_appointments = random.randint(1, 3)
                
                for i in range(num_appointments):
                    appointment_date = timezone.now().date() + timedelta(days=random.randint(-30, 30))
                    appointment_time = datetime.combine(appointment_date, datetime.min.time().replace(
                        hour=random.randint(8, 17),
                        minute=random.choice([0, 15, 30, 45])
                    )).time()
                    
                    appointment = Appointment.objects.create(
                        patient=patient,
                        procedure_type=random.choice(procedure_choices),
                        appointment_date=appointment_date,
                        appointment_time=appointment_time,
                        reason=f"Appointment reason for {patient.first_name}",
                        notes=f"Appointment notes {i+1}",
                        status=random.choice(statuses),
                        created_at=timezone.now() - timedelta(days=random.randint(1, 100))
                    )
                    appointments.append(appointment)
                    
        return appointments

    def create_bills_and_payments(self, exams):
        """Create bills and payments for exams"""
        bills = []
        payment_methods = ['CASH', 'GCASH', 'BANK']
        
        # Group exams by patient and date
        patient_exam_groups = {}
        for exam in exams:
            key = (exam.patient, exam.exam_date)
            if key not in patient_exam_groups:
                patient_exam_groups[key] = []
            patient_exam_groups[key].append(exam)
        
        for (patient, exam_date), exam_list in patient_exam_groups.items():
            # Only create bills for 80% of exam groups
            if random.random() < 0.8:
                # Calculate total amount
                total_amount = sum(exam.procedure_type.base_price for exam in exam_list)
                
                # Create bill
                discount_amount = Decimal(random.randint(0, int(total_amount * Decimal('0.1'))))  # 0-10% discount
                bill = Bill.objects.create(
                    patient=patient,
                    bill_date=exam_date,
                    subtotal=total_amount,
                    discount=discount_amount,
                    tax=Decimal(0),  # No tax for simplicity
                    total_amount=total_amount - discount_amount,
                    status=random.choice(['PENDING', 'PARTIAL', 'PAID', 'CANCELLED']),
                    notes=f"Bill for {len(exam_list)} procedures on {exam_date}",
                    created_at=timezone.now() - timedelta(days=random.randint(1, 365))
                )
                
                # Create bill items
                for exam in exam_list:
                    BillItem.objects.create(
                        bill=bill,
                        exam=exam,
                        service=exam.procedure_type,
                        amount=exam.procedure_type.base_price,
                        notes=f"Bill item for {exam.procedure_type.name}"
                    )
                
                # Create payments for PAID and PARTIAL bills
                if bill.status in ['PAID', 'PARTIAL']:
                    self.create_payments_for_bill(bill)
                
                bills.append(bill)
                
        return bills

    def create_payments_for_bill(self, bill):
        """Create payments for a bill"""
        payment_methods = ['CASH', 'GCASH', 'BANK']
        
        if bill.status == 'PAID':
            # Single payment for full amount
            Payment.objects.create(
                bill=bill,
                amount=bill.total_amount,
                payment_date=bill.bill_date + timedelta(days=random.randint(0, 30)),
                payment_method=random.choice(payment_methods),
                reference_number=f"REF{random.randint(100000, 999999)}" if random.choice(payment_methods) != 'CASH' else "",
                notes="Full payment",
                created_by=f"Staff {random.randint(1, 5)}"
            )
        elif bill.status == 'PARTIAL':
            # Multiple partial payments
            remaining_amount = bill.total_amount
            num_payments = random.randint(2, 4)
            
            for i in range(num_payments):
                if remaining_amount <= 0:
                    break
                    
                if i == num_payments - 1:  # Last payment
                    payment_amount = remaining_amount
                else:
                    max_payment = int(remaining_amount * Decimal('0.7'))
                    if max_payment > 100:
                        payment_amount = Decimal(random.randint(100, max_payment))
                    else:
                        payment_amount = Decimal(random.randint(50, max_payment)) if max_payment > 50 else remaining_amount
                
                Payment.objects.create(
                    bill=bill,
                    amount=payment_amount,
                    payment_date=bill.bill_date + timedelta(days=random.randint(0, 30)),
                    payment_method=random.choice(payment_methods),
                    reference_number=f"REF{random.randint(100000, 999999)}" if random.choice(payment_methods) != 'CASH' else "",
                    notes=f"Partial payment {i+1}",
                    created_by=f"Staff {random.randint(1, 5)}"
                )
                
                remaining_amount -= payment_amount
