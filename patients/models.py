from django.db import models
from django.utils import timezone

class Patient(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    
    name = models.CharField(max_length=100)
    age = models.IntegerField()
    sex = models.CharField(max_length=1, choices=GENDER_CHOICES)
    date_of_birth = models.DateField()
    address = models.TextField()
    contact_number = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    emergency_contact = models.CharField(max_length=100, blank=True, null=True)
    emergency_contact_number = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.contact_number}"

    class Meta:
        ordering = ['-created_at']

class UltrasoundExam(models.Model):
    PROCEDURE_CHOICES = [
        ('ABD', 'Abdominal'),
        ('PEL', 'Pelvic'),
        ('OBS', 'Obstetric'),
        ('TVS', 'Transvaginal'),
        ('BRE', 'Breast'),
        ('THY', 'Thyroid'),
        ('SCR', 'Scrotal'),
        ('DOP', 'Doppler'),
        ('OTH', 'Other'),
    ]

    RECOMMENDATION_CHOICES = [
        ('FI', 'Further imaging'),
        ('FU', 'Follow-up ultrasound'),
        ('RS', 'Referral to specialist'),
        ('BI', 'Biopsy/FNA advised'),
        ('NF', 'No further workup needed'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='ultrasound_exams')
    referring_physician = models.CharField(max_length=100)
    clinical_diagnosis = models.TextField()
    medical_history = models.TextField()
    
    # Procedure Details
    procedure_type = models.CharField(max_length=3, choices=PROCEDURE_CHOICES)
    doppler_site = models.CharField(max_length=100, blank=True, null=True)
    other_procedure = models.CharField(max_length=100, blank=True, null=True)
    
    exam_date = models.DateField()
    exam_time = models.TimeField()
    technologist = models.CharField(max_length=100)
    radiologist = models.CharField(max_length=100)
    
    # Findings and Impressions
    findings = models.TextField()
    impression = models.TextField()
    
    # Recommendations
    recommendations = models.CharField(max_length=2, choices=RECOMMENDATION_CHOICES)
    followup_duration = models.CharField(max_length=50, blank=True, null=True)
    specialist_referral = models.CharField(max_length=100, blank=True, null=True)
    
    technologist_notes = models.TextField(blank=True, null=True)
    technologist_signature = models.CharField(max_length=100)
    radiologist_signature = models.CharField(max_length=100)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.patient.name} - {self.procedure_type} - {self.exam_date}"

    class Meta:
        ordering = ['-exam_date', '-exam_time'] 