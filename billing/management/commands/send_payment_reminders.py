from django.core.management.base import BaseCommand
from django.utils import timezone
from billing.models import Bill

class Command(BaseCommand):
    help = 'Send payment reminders for overdue bills'

    def handle(self, *args, **kwargs):
        # Get all overdue bills that haven't been paid
        overdue_bills = Bill.objects.filter(
            due_date__lt=timezone.now().date(),
            status__in=['PENDING', 'PARTIAL']
        )

        reminders_sent = 0
        for bill in overdue_bills:
            if bill.send_payment_reminder():
                reminders_sent += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully sent reminder for Bill #{bill.bill_number}'
                    )
                )
            
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully sent {reminders_sent} payment reminders'
            )
        ) 