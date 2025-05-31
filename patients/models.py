from django.db import models
from django.utils import timezone
import json
import os
from django.conf import settings

class Patient(models.Model):
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
    
    first_name = models.CharField(max_length=50, verbose_name="First Name")
    last_name = models.CharField(max_length=50, verbose_name="Last Name")
    age = models.IntegerField()
    sex = models.CharField(max_length=1, choices=GENDER_CHOICES)
    date_of_birth = models.DateField()
    patient_type = models.CharField(max_length=10, choices=PATIENT_TYPE_CHOICES, default='REGULAR')
    id_number = models.CharField(max_length=50, blank=True, null=True, help_text="Senior Citizen/PWD ID number")
    
    # Address fields as simple text fields
    region = models.CharField("Region", max_length=100)
    province = models.CharField("Province", max_length=100)
    city = models.CharField("City/Municipality", max_length=100)
    barangay = models.CharField("Barangay", max_length=100)
    street_address = models.TextField(help_text="House/Building Number, Street Name, etc.")
    
    contact_number = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    emergency_contact = models.CharField(max_length=100, blank=True, null=True)
    emergency_contact_number = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.contact_number}"

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
        province = next((p for p in provinces if p['province_code'] == self.province), None)
        return province['province_name'] if province else self.province

    @property
    def city_name(self):
        cities = self._load_json_data('city.json')
        city = next((c for c in cities if c['city_code'] == self.city), None)
        return city['city_name'] if city else self.city

    @property
    def barangay_name(self):
        barangays = self._load_json_data('barangay.json')
        barangay = next((b for b in barangays if b['brgy_code'] == self.barangay), None)
        return barangay['brgy_name'] if barangay else self.barangay

    class Meta:
        ordering = ['-created_at']

class UltrasoundExam(models.Model):
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
    
    # Image and Annotations
    image = models.ImageField(upload_to='ultrasound_images/', null=True, blank=True)
    annotations = models.TextField(null=True, blank=True)
    
    # Procedure Details
    procedure_type = models.ForeignKey('billing.ServiceType', on_delete=models.PROTECT, related_name='ultrasound_exams')
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
        return f"{self.patient.first_name} {self.patient.last_name} - {self.procedure_type} - {self.exam_date}"

    class Meta:
        ordering = ['-exam_date', '-exam_time'] 