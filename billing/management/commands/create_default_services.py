from django.core.management.base import BaseCommand
from billing.models import ServiceType

class Command(BaseCommand):
    help = 'Creates default service types for the billing system'

    def handle(self, *args, **kwargs):
        default_services = [
            {
                'name': 'Abdominal Ultrasound',
                'description': 'Complete examination of the abdominal organs',
                'base_price': 2500.00,
            },
            {
                'name': 'Breast Ultrasound',
                'description': 'Bilateral breast examination',
                'base_price': 2000.00,
            },
            {
                'name': 'Thyroid Ultrasound',
                'description': 'Examination of the thyroid gland',
                'base_price': 1800.00,
            },
            {
                'name': 'Pelvic Ultrasound',
                'description': 'Examination of the pelvic organs',
                'base_price': 2200.00,
            },
            {
                'name': 'Obstetric Ultrasound',
                'description': 'Pregnancy examination',
                'base_price': 2500.00,
            },
        ]

        for service_data in default_services:
            service, created = ServiceType.objects.get_or_create(
                name=service_data['name'],
                defaults={
                    'description': service_data['description'],
                    'base_price': service_data['base_price'],
                    'is_active': True,
                }
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created service type: {service.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Service type already exists: {service.name}')
                ) 