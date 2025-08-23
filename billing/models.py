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
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        return f"{self.name} - ₱{self.base_price}"

class Bill(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PARTIAL', 'Partially Paid'),
        ('PAID', 'Fully Paid'),
        ('CANCELLED', 'Cancelled'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'Cash'),
        ('GCASH', 'GCash'),
        ('BANK', 'Bank Transfer'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='bills')
    bill_number = models.CharField(max_length=50, unique=True)
    bill_date = models.DateField()
    
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_reminder_sent = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Bill #{self.bill_number} - {self.patient}"

    def save(self, *args, **kwargs):
        if not self.bill_number:
            last_bill = Bill.objects.order_by('-id').first()
            if last_bill:
                last_number = int(last_bill.bill_number[4:])
                self.bill_number = f'BILL{str(last_number + 1).zfill(6)}'
            else:
                self.bill_number = 'BILL000001'
            
        self.total_amount = self.subtotal - self.discount + self.tax
        super().save(*args, **kwargs)

    def calculate_totals(self):
        """Calculate totals based on bill items"""
        self.subtotal = sum(item.amount for item in self.items.all())
        self.total_amount = self.subtotal - self.discount + self.tax
        self.save()

    def send_payment_reminder(self):
        if (self.last_reminder_sent and 
            timezone.now() - self.last_reminder_sent < timezone.timedelta(days=7)):
            return False  # Don't send reminders more often than weekly

        context = {
            'bill': self,
            'patient': self.patient,
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

    def update_status(self):
        """Update bill status based on payments."""
        total_paid = sum(payment.amount for payment in self.payments.all())
        
        if total_paid >= self.total_amount:
            self.status = 'PAID'
        elif total_paid > 0:
            self.status = 'PARTIAL'
        else:
            self.status = 'PENDING'
        
        self.save()

    def is_fully_paid(self):
        """Check if the bill is fully paid."""
        total_paid = sum(payment.amount for payment in self.payments.all())
        return total_paid >= self.total_amount

    def get_total_paid_before_payment(self, exclude_payment=None):
        """Get total amount paid excluding a specific payment (useful for change calculation)"""
        if exclude_payment:
            return sum(payment.amount for payment in self.payments.all() if payment != exclude_payment)
        return sum(payment.amount for payment in self.payments.all())

    def get_total_change_given(self):
        """Get total change given to patient across all payments"""
        return sum(payment.change for payment in self.payments.all())

class BillItem(models.Model):
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='items')
    exam = models.OneToOneField(UltrasoundExam, on_delete=models.CASCADE, related_name='bill_item')
    service = models.ForeignKey(ServiceType, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True, null=True)

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
    change = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Change to be given to patient")
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=100)  # Name of staff who recorded the payment

    def __str__(self):
        return f"Payment of ₱{self.amount} for {self.bill.bill_number}"

    def calculate_change(self):
        """Calculate change if payment amount exceeds bill amount"""
        # Get total paid before this payment
        total_paid_before = self.bill.get_total_paid_before_payment(self)
        
        # Calculate how much is still needed to pay the bill
        remaining_needed = self.bill.total_amount - total_paid_before
        
        if remaining_needed <= 0:
            # Bill is already fully paid, this payment is all change
            self.change = self.amount
        elif self.amount > remaining_needed:
            # Payment exceeds what's needed, calculate change
            self.change = self.amount - remaining_needed
        else:
            # Payment is exactly what's needed or less, no change
            self.change = 0
        
        return self.change

    def save(self, *args, **kwargs):
        # Calculate change before saving
        self.calculate_change()
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
