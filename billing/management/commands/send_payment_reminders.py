from django.core.management.base import BaseCommand
from django.utils import timezone
from billing.models import Bill

class Command(BaseCommand):
    help = 'Send payment reminders for pending bills'

    def handle(self, *args, **kwargs):
        # Get all pending bills that haven't been paid
        pending_bills = Bill.objects.filter(
            status__in=['PENDING', 'PARTIAL']
        )

        reminders_sent = 0
        for bill in pending_bills:
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