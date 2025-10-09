from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from datetime import date, timedelta, time
import random
from decimal import Decimal

from billing.models import ServiceType, Bill, BillItem, Payment
from patients.models import Patient, UltrasoundExam, FamilyGroup

class Command(BaseCommand):
    help = 'Generates 100 dummy billing records with all bills paid and no discounts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=100,
            help='Number of dummy billing records to generate (default: 100)'
        )

    def handle(self, *args, **kwargs):
        count = kwargs['count']
        
        # Ensure we have service types
        self.ensure_service_types()
        
        # Create family groups
        family_groups = self.create_family_groups()
        
        # Generate dummy patients
        patients = self.create_dummy_patients(count, family_groups)
        
        # Generate ultrasound exams for each patient
        exams = self.create_dummy_exams(patients)
        
        # Generate bills and payments
        self.create_dummy_bills_and_payments(exams)
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully generated {count} dummy billing records!')
        )

    def ensure_service_types(self):
        """Ensure we have service types available"""
        if not ServiceType.objects.exists():
            self.stdout.write('Creating default service types...')
            from billing.management.commands.create_default_services import Command as CreateServicesCommand
            create_services = CreateServicesCommand()
            create_services.handle()

    def create_family_groups(self):
        """Create some family groups"""
        family_names = [
            'Santos Family', 'Garcia Family', 'Reyes Family', 'Cruz Family',
            'Lopez Family', 'Martinez Family', 'Gonzalez Family', 'Rodriguez Family',
            'Perez Family', 'Sanchez Family'
        ]
        
        family_groups = []
        for name in family_names:
            group, created = FamilyGroup.objects.get_or_create(name=name)
            family_groups.append(group)
            if created:
                self.stdout.write(f'Created family group: {name}')
        
        return family_groups

    def create_dummy_patients(self, count, family_groups):
        """Create dummy patients with realistic data"""
        first_names = [
            'Maria', 'Jose', 'Ana', 'Juan', 'Carmen', 'Pedro', 'Rosa', 'Carlos',
            'Elena', 'Miguel', 'Isabel', 'Antonio', 'Dolores', 'Francisco', 'Pilar',
            'Manuel', 'Teresa', 'Javier', 'Concepcion', 'Rafael', 'Mercedes', 'Luis',
            'Josefa', 'Fernando', 'Dolores', 'Angel', 'Amparo', 'Diego', 'Rosario',
            'Sergio', 'Cristina', 'Alberto', 'Victoria', 'Roberto', 'Beatriz', 'David',
            'Nuria', 'Alejandro', 'Sofia', 'Pablo', 'Lucia', 'Adrian', 'Patricia',
            'Raul', 'Monica', 'Sergio', 'Elena', 'Ivan', 'Laura', 'Oscar', 'Marta'
        ]
        
        last_names = [
            'Santos', 'Garcia', 'Reyes', 'Cruz', 'Lopez', 'Martinez', 'Gonzalez',
            'Rodriguez', 'Perez', 'Sanchez', 'Ramirez', 'Torres', 'Flores', 'Rivera',
            'Gomez', 'Diaz', 'Herrera', 'Jimenez', 'Moreno', 'Munoz', 'Alvarez',
            'Romero', 'Navarro', 'Ruiz', 'Serrano', 'Blanco', 'Molina', 'Morales',
            'Ortega', 'Delgado', 'Castro', 'Ortiz', 'Rubio', 'Marin', 'Sanz',
            'Iglesias', 'Medina', 'Cortes', 'Garrido', 'Castillo', 'Vazquez',
            'Ramos', 'Gil', 'Leon', 'Herrero', 'Vega', 'Campos', 'Calvo', 'Vidal'
        ]
        
        regions = ['NCR', 'Region III', 'Region IV-A', 'Region VII', 'Region XI']
        provinces = ['Metro Manila', 'Bulacan', 'Cavite', 'Laguna', 'Cebu', 'Davao']
        cities = ['Quezon City', 'Manila', 'Makati', 'Taguig', 'Pasig', 'Mandaluyong']
        barangays = ['Barangay 1', 'Barangay 2', 'Barangay 3', 'Barangay 4', 'Barangay 5']
        
        patients = []
        
        for i in range(count):
            # Create user account
            username = f'patient_{i+1:03d}'
            email = f'patient{i+1}@example.com'
            
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': random.choice(first_names),
                    'last_name': random.choice(last_names),
                }
            )
            
            if created:
                user.set_password('password123')
                user.save()
            
            # Create patient
            patient, created = Patient.objects.get_or_create(
                user=user,
                defaults={
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'birthday': date.today() - timedelta(days=random.randint(18*365, 80*365)),
                    'sex': random.choice(['M', 'F']),
                    'marital_status': random.choice(['S', 'M', 'W', 'D']),
                    'patient_type': random.choice(['REGULAR', 'SENIOR', 'PWD']),
                    'patient_status': random.choice(['IN', 'OUT']),
                    'region': random.choice(regions),
                    'province': random.choice(provinces),
                    'city': random.choice(cities),
                    'barangay': random.choice(barangays),
                    'street_address': f'{random.randint(1, 999)} Sample Street',
                    'contact_number': f'09{random.randint(100000000, 999999999)}',
                    'email': email,
                    'family_group': random.choice(family_groups) if random.random() < 0.3 else None,
                }
            )
            
            if created:
                patients.append(patient)
                self.stdout.write(f'Created patient: {patient.first_name} {patient.last_name}')
        
        return patients

    def create_dummy_exams(self, patients):
        """Create ultrasound exams for patients"""
        service_types = list(ServiceType.objects.all())
        if not service_types:
            self.stdout.write(self.style.ERROR('No service types found!'))
            return []
        
        physicians = [
            'Dr. Maria Santos', 'Dr. Juan Garcia', 'Dr. Ana Reyes', 'Dr. Carlos Cruz',
            'Dr. Elena Lopez', 'Dr. Pedro Martinez', 'Dr. Rosa Gonzalez', 'Dr. Miguel Rodriguez',
            'Dr. Isabel Perez', 'Dr. Antonio Sanchez'
        ]
        
        technicians = [
            'Tech. Maria', 'Tech. Juan', 'Tech. Ana', 'Tech. Carlos', 'Tech. Elena'
        ]
        
        findings_templates = [
            'Normal examination with no significant abnormalities detected.',
            'Mild findings consistent with age-related changes.',
            'Unremarkable examination within normal limits.',
            'Stable findings compared to previous examination.',
            'Normal organ morphology and echotexture.',
        ]
        
        impression_templates = [
            'Normal examination.',
            'No acute findings.',
            'Stable condition.',
            'Within normal limits.',
            'No significant abnormalities.',
        ]
        
        exams = []
        
        for patient in patients:
            # Create 1-3 exams per patient
            num_exams = random.randint(1, 3)
            
            for _ in range(num_exams):
                exam_date = date.today() - timedelta(days=random.randint(1, 365))
                exam_time = time(random.randint(8, 17), random.choice([0, 15, 30, 45]))
                
                exam = UltrasoundExam.objects.create(
                    patient=patient,
                    status='COMPLETED',
                    referring_physician=random.choice(physicians),
                    procedure_type=random.choice(service_types),
                    exam_date=exam_date,
                    exam_time=exam_time,
                    findings=random.choice(findings_templates),
                    impression=random.choice(impression_templates),
                    recommendations=random.choice(['FI', 'FU', 'RS', 'BI', 'NF']),
                    technician=random.choice(technicians),
                    notes=f'Exam performed on {exam_date.strftime("%B %d, %Y")}',
                )
                
                exams.append(exam)
        
        self.stdout.write(f'Created {len(exams)} ultrasound exams')
        return exams

    def create_dummy_bills_and_payments(self, exams):
        """Create bills and payments for exams"""
        payment_methods = ['CASH', 'GCASH', 'BANK']
        staff_members = [
            'Admin User', 'Staff Member 1', 'Staff Member 2', 'Receptionist',
            'Billing Staff', 'Office Manager'
        ]
        
        bills_created = 0
        payments_created = 0
        
        for exam in exams:
            # Create bill
            bill = Bill.objects.create(
                patient=exam.patient,
                bill_date=exam.exam_date,
                subtotal=exam.procedure_type.base_price,
                discount=Decimal('0.00'),  # No discount as requested
                tax=Decimal('0.00'),  # No tax for simplicity
                total_amount=exam.procedure_type.base_price,
                status='PAID',  # All bills are paid as requested
                notes=f'Payment for {exam.procedure_type.name} examination',
            )
            
            bills_created += 1
            
            # Create payment to make bill fully paid
            payment = Payment.objects.create(
                bill=bill,
                amount=exam.procedure_type.base_price,
                payment_date=exam.exam_date,
                payment_method=random.choice(payment_methods),
                reference_number=f'REF{random.randint(100000, 999999)}' if random.choice(payment_methods) != 'CASH' else '',
                notes=f'Full payment for {exam.procedure_type.name}',
                change=Decimal('0.00'),
                created_by=random.choice(staff_members),
            )
            
            payments_created += 1
            
            # Create bill item
            BillItem.objects.create(
                bill=bill,
                exam=exam,
                service=exam.procedure_type,
                amount=exam.procedure_type.base_price,
                notes=f'Service for {exam.exam_date}',
            )
        
        self.stdout.write(f'Created {bills_created} bills and {payments_created} payments')
