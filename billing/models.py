from django.db import models
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from patients.models import Patient, UltrasoundExam

class ServiceType(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - ₱{self.base_price}"

class Bill(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PARTIAL', 'Partially Paid'),
        ('PAID', 'Paid'),
        ('CANCELLED', 'Cancelled'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'Cash'),
        ('CARD', 'Credit/Debit Card'),
        ('GCASH', 'GCash'),
        ('MAYA', 'Maya'),
        ('BANK', 'Bank Transfer'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='bills')
    bill_number = models.CharField(max_length=20, unique=True)
    bill_date = models.DateField(default=timezone.now)
    due_date = models.DateField()
    
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_reminder_sent = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Bill #{self.bill_number} - {self.patient.first_name} {self.patient.last_name}"

    def save(self, *args, **kwargs):
        if not self.bill_number:
            last_bill = Bill.objects.order_by('-id').first()
            if last_bill:
                last_number = int(last_bill.bill_number[4:])
                self.bill_number = f'BILL{str(last_number + 1).zfill(6)}'
            else:
                self.bill_number = 'BILL000001'
        
        if not self.due_date:
            self.due_date = self.bill_date + timezone.timedelta(days=30)
            
        self.total_amount = self.subtotal - self.discount + self.tax
        super().save(*args, **kwargs)

    def is_overdue(self):
        return self.due_date < timezone.now().date() and self.status not in ['PAID', 'CANCELLED']

    def get_remaining_balance(self):
        total_paid = sum(payment.amount for payment in self.payments.all())
        return self.total_amount - total_paid

    def get_days_overdue(self):
        if self.is_overdue():
            return (timezone.now().date() - self.due_date).days
        return 0

    def calculate_totals(self):
        """Calculate totals based on bill items"""
        self.subtotal = sum(item.amount for item in self.items.all())
        self.total_amount = self.subtotal - self.discount + self.tax
        self.save()

    def send_payment_reminder(self):
        if not self.is_overdue():
            return False

        if (self.last_reminder_sent and 
            timezone.now() - self.last_reminder_sent < timezone.timedelta(days=7)):
            return False  # Don't send reminders more often than weekly

        context = {
            'bill': self,
            'patient': self.patient,
            'remaining_balance': self.get_remaining_balance(),
            'days_overdue': self.get_days_overdue(),
            'clinic_name': 'Ultrasound Clinic',
            'clinic_phone': settings.CLINIC_PHONE,
            'clinic_email': settings.DEFAULT_FROM_EMAIL,
        }

        subject = f'Payment Reminder - Bill #{self.bill_number}'
        html_message = render_to_string('billing/email/payment_reminder.html', context)
        plain_message = render_to_string('billing/email/payment_reminder_plain.txt', context)

        try:
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[self.patient.email],
                html_message=html_message
            )
            self.last_reminder_sent = timezone.now()
            self.save(update_fields=['last_reminder_sent'])
            return True
        except Exception as e:
            print(f"Failed to send payment reminder: {str(e)}")
            return False

class BillItem(models.Model):
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='items')
    exam = models.OneToOneField(UltrasoundExam, on_delete=models.CASCADE, related_name='bill_item')
    service = models.ForeignKey(ServiceType, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.service.name} - {self.exam.exam_date}"

    def save(self, *args, **kwargs):
        if not self.amount:
            self.amount = self.service.base_price
        super().save(*args, **kwargs)
        self.bill.calculate_totals()

class Payment(models.Model):
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField(default=timezone.now)
    payment_method = models.CharField(max_length=20, choices=Bill.PAYMENT_METHOD_CHOICES)
    
    reference_number = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=100)  # Name of staff who recorded the payment

    def __str__(self):
        return f"Payment of ₱{self.amount} for {self.bill.bill_number}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Update bill status based on total payments
        bill = self.bill
        total_paid = sum(payment.amount for payment in bill.payments.all())
        
        if total_paid >= bill.total_amount:
            bill.status = 'PAID'
        elif total_paid > 0:
            bill.status = 'PARTIAL'
        else:
            bill.status = 'PENDING'
        
        bill.save()
