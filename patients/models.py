from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
import json
import os
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator

class FamilyGroup(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Patient(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name='patient')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_patients', verbose_name='Created By')
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    
    PATIENT_TYPE_CHOICES = [
        ('REGULAR', 'Regular'),
        ('SENIOR', 'Senior Citizen'),
        ('PWD', 'Person with Disability'),
    ]

    PATIENT_STATUS_CHOICES = [
        ('IN', 'Inpatient'),
        ('OUT', 'Outpatient'),
    ]

    MARITAL_STATUS_CHOICES = [
        ('S', 'Single'),
        ('M', 'Married'),
        ('W', 'Widowed'),
        ('D', 'Divorced'),
    ]
    
    first_name = models.CharField(max_length=50, verbose_name="First Name", default="")
    last_name = models.CharField(max_length=50, verbose_name="Last Name", default="")
    birthday = models.DateField(null=True, blank=True)
    sex = models.CharField(max_length=1, choices=GENDER_CHOICES)
    marital_status = models.CharField(max_length=1, choices=MARITAL_STATUS_CHOICES, null=True, blank=True)
    patient_type = models.CharField(max_length=10, choices=PATIENT_TYPE_CHOICES, default='REGULAR')
    patient_status = models.CharField(max_length=3, choices=PATIENT_STATUS_CHOICES, default='OUT')
    id_number = models.CharField(max_length=50, blank=True, null=True, help_text="Senior Citizen/PWD ID number")
    family_group = models.ForeignKey(FamilyGroup, on_delete=models.SET_NULL, null=True, blank=True, related_name='family_members')
    
    # Address fields as simple text fields
    region = models.CharField("Region", max_length=100)
    province = models.CharField("Province", max_length=100)
    city = models.CharField("City/Municipality", max_length=100)
    barangay = models.CharField("Barangay", max_length=100)
    street_address = models.TextField(help_text="House/Building Number, Street Name, etc.")
    
    contact_number = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_archived = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.contact_number}"

    def delete(self, using=None, keep_parents=False):
        """Soft-delete: archive instead of removing from the database.
        If already archived, perform a hard delete via hard_delete().
        """
        if not self.is_archived:
            self.is_archived = True
            self.archived_at = timezone.now()
            self.save(update_fields=['is_archived', 'archived_at'])
            return
        # If already archived, allow hard deletion explicitly
        return self.hard_delete(using=using, keep_parents=keep_parents)

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)

    def _load_json_data(self, filename):
        file_path = os.path.join(settings.BASE_DIR, 'static', 'philippine-addresses', filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            return []

    @property
    def region_name(self):
        regions = self._load_json_data('region.json')
        region = next((r for r in regions if r['region_code'] == self.region), None)
        return region['region_name'] if region else self.region

    @property
    def province_name(self):
        provinces = self._load_json_data('province.json')
        # Ensure province code is padded to 4 digits
        province_code = self.province.zfill(4) if self.province else None
        province = next((p for p in provinces if p['province_code'] == province_code), None)
        return province['province_name'] if province else self.province

    @property
    def city_name(self):
        cities = self._load_json_data('city.json')
        # Ensure city code is padded to 6 digits
        city_code = self.city.zfill(6) if self.city else None
        city = next((c for c in cities if c['city_code'] == city_code), None)
        return city['city_name'] if city else self.city

    @property
    def barangay_name(self):
        barangays = self._load_json_data('barangay.json')
        # Ensure barangay code is padded to 9 digits
        barangay_code = self.barangay.zfill(9) if self.barangay else None
        barangay = next((b for b in barangays if b['brgy_code'] == barangay_code), None)
        return barangay['brgy_name'] if barangay else self.barangay

    @property
    def age(self):
        """Calculate age based on birthday field."""
        from datetime import date
        if self.birthday:
            today = date.today()
            return today.year - self.birthday.year - ((today.month, today.day) < (self.birthday.month, self.birthday.day))
        return None

    @property
    def date_of_birth(self):
        """Return the birthday field for template compatibility."""
        return self.birthday

    class Meta:
        ordering = ['-created_at']

class UltrasoundImage(models.Model):
    exam = models.ForeignKey('UltrasoundExam', on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='ultrasound_images/')
    annotated_image = models.ImageField(upload_to='annotated_images/', null=True, blank=True)
    caption = models.CharField(max_length=200, blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    annotations = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"Image for {self.exam} - {self.uploaded_at}"

# class BaseMeasurements(models.Model):
#     ultrasound_image = models.ForeignKey(UltrasoundImage, on_delete=models.CASCADE)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         abstract = True

# class PelvicUltrasoundMeasurements(BaseMeasurements):
#     uterus_length = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text='cm')
#     uterus_width = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text='cm')
#     endometrial_thickness = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text='mm')
#     right_ovary_location = models.CharField(max_length=100, null=True, blank=True)
#     left_ovary_location = models.CharField(max_length=100, null=True, blank=True)

#     def __str__(self):
#         return f"Pelvic Measurements for {self.ultrasound_image}"

# class AbdominalUltrasoundMeasurements(BaseMeasurements):
#     liver_size = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text='cm')
#     liver_location = models.CharField(max_length=100, null=True, blank=True)
#     gallbladder_location = models.CharField(max_length=100, null=True, blank=True)
#     spleen_size = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text='cm')
#     kidney_right_size = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text='cm')
#     kidney_left_size = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text='cm')

#     def __str__(self):
#         return f"Abdominal Measurements for {self.ultrasound_image}"

# class BreastUltrasoundMeasurements(BaseMeasurements):
#     mass_location = models.CharField(max_length=100, null=True, blank=True)
#     mass_size = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text='cm')
#     distance_from_nipple = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text='cm')

#     def __str__(self):
#         return f"Breast Measurements for {self.ultrasound_image}"

# class ThyroidUltrasoundMeasurements(BaseMeasurements):
#     right_lobe_size = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text='cm')
#     left_lobe_size = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text='cm')
#     nodule_location = models.CharField(max_length=100, null=True, blank=True)
#     nodule_size = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text='mm')

#     def __str__(self):
#         return f"Thyroid Measurements for {self.ultrasound_image}"

class UltrasoundExam(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    RECOMMENDATION_CHOICES = [
        ('FI', 'Further imaging'),
        ('FU', 'Follow-up ultrasound'),
        ('RS', 'Referral to specialist'),
        ('BI', 'Biopsy/FNA advised'),
        ('NF', 'No further workup needed'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='ultrasound_exams')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    referring_physician = models.CharField(max_length=100)
    
    # Procedure Details
    procedure_type = models.ForeignKey('billing.ServiceType', on_delete=models.PROTECT, related_name='ultrasound_exams')
    
    exam_date = models.DateField()
    exam_time = models.TimeField()
    
    # Findings and Impressions
    findings = models.TextField(default='')
    impression = models.TextField(default='')
    
    # Recommendations
    recommendations = models.CharField(max_length=2, choices=RECOMMENDATION_CHOICES, default='NF')
    followup_duration = models.CharField(max_length=50, blank=True, null=True)
    specialist_referral = models.CharField(max_length=100, blank=True, null=True)
    
    # Additional fields
    technician = models.CharField(max_length=100, blank=True, null=True, help_text="Technician who performed the exam")
    notes = models.TextField(blank=True, null=True, help_text="Additional notes about the examination")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.patient.first_name} {self.patient.last_name} - {self.exam_date}"

    class Meta:
        ordering = ['-exam_date', '-exam_time'] 

class Appointment(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
        ('COMPLETED', 'Completed'),
    ]
    
    PROCEDURE_CHOICES = [
        ('ABD', 'Abdominal Ultrasound'),
        ('PEL', 'Pelvic Ultrasound'),
        ('OBS', 'Obstetric Ultrasound'),
        ('TVS', 'Transvaginal Ultrasound'),
        ('BRE', 'Breast Ultrasound'),
        ('THY', 'Thyroid Ultrasound'),
        ('SCR', 'Scrotal Ultrasound'),
        ('DOP', 'Doppler Ultrasound'),
        ('OTH', 'Other'),
    ]
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='appointments')
    procedure_type = models.TextField()
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    reason = models.TextField(help_text="Reason for appointment or symptoms")
    notes = models.TextField(blank=True, null=True, help_text="Additional notes")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_on = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-appointment_date', '-appointment_time']
    
    def __str__(self):
        return f"{self.patient.first_name} {self.patient.last_name} - {self.procedure_type} on {self.appointment_date}"
    
    @property
    def is_past_due(self):
        from django.utils import timezone
        from datetime import datetime
        appointment_datetime = datetime.combine(self.appointment_date, self.appointment_time)
        return appointment_datetime < timezone.now()
    
    @property
    def is_today(self):
        from django.utils import timezone
        return self.appointment_date == timezone.now().date()
    
    @property
    def is_overdue_by_3_days(self):
        """Check if appointment is 3 or more days past the appointment date."""
        from django.utils import timezone
        from datetime import timedelta
        today = timezone.now().date()
        three_days_ago = today - timedelta(days=3)
        return self.appointment_date < three_days_ago
    
    def cancel_if_overdue(self):
        """Cancel the appointment if it's 3 or more days overdue."""
        if self.is_overdue_by_3_days and self.status in ['PENDING', 'CONFIRMED']:
            self.status = 'CANCELLED'
            self.save(update_fields=['status', 'updated_at'])
            return True
        return False
    
    @classmethod
    def cancel_overdue_appointments(cls, days_overdue=3):
        """Cancel all appointments that are overdue by the specified number of days."""
        from django.utils import timezone
        from datetime import timedelta
        
        today = timezone.now().date()
        cutoff_date = today - timedelta(days=days_overdue)
        
        overdue_appointments = cls.objects.filter(
            appointment_date__lt=cutoff_date,
            status__in=['PENDING', 'CONFIRMED']
        )
        
        count = overdue_appointments.update(status='CANCELLED')
        return count

    def save(self, *args, **kwargs):
        from django.utils import timezone
        try:
            old_instance = type(self).objects.get(pk=self.pk)
            old_status = old_instance.status
        except type(self).DoesNotExist:
            old_status = None

        if self.status == 'COMPLETED' and (old_status != 'COMPLETED' or self.completed_on is None):
            self.completed_on = timezone.now()
        elif self.status != 'COMPLETED':
            self.completed_on = None

        super().save(*args, **kwargs)

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('APPOINTMENT_BOOKED', 'New Appointment Booked'),
        ('APPOINTMENT_CONFIRMED', 'Appointment Confirmed'),
        ('APPOINTMENT_CANCELLED', 'Appointment Cancelled'),
        ('APPOINTMENT_UPDATED', 'Appointment Updated'),
        ('EXAM_CREATED', 'New Exam Created'),
        ('EXAM_UPDATED', 'Exam Updated'),
        ('EXAM_COMPLETED', 'Exam Completed'),
        ('GENERAL', 'General Notification'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=25, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.user.username}" 