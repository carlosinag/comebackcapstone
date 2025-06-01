from django.db import models
from django.utils import timezone
import json
import os
from django.conf import settings

class FamilyGroup(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

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
    age = models.IntegerField()
    sex = models.CharField(max_length=1, choices=GENDER_CHOICES)
    date_of_birth = models.DateField()
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

class BaseMeasurements(models.Model):
    ultrasound_image = models.ForeignKey(UltrasoundImage, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class PelvicUltrasoundMeasurements(BaseMeasurements):
    uterus_length = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text='cm')
    uterus_width = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text='cm')
    endometrial_thickness = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text='mm')
    right_ovary_location = models.CharField(max_length=100, null=True, blank=True)
    left_ovary_location = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"Pelvic Measurements for {self.ultrasound_image}"

class AbdominalUltrasoundMeasurements(BaseMeasurements):
    liver_size = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text='cm')
    liver_location = models.CharField(max_length=100, null=True, blank=True)
    gallbladder_location = models.CharField(max_length=100, null=True, blank=True)
    spleen_size = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text='cm')
    kidney_right_size = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text='cm')
    kidney_left_size = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text='cm')

    def __str__(self):
        return f"Abdominal Measurements for {self.ultrasound_image}"

class BreastUltrasoundMeasurements(BaseMeasurements):
    mass_location = models.CharField(max_length=100, null=True, blank=True)
    mass_size = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text='cm')
    distance_from_nipple = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text='cm')

    def __str__(self):
        return f"Breast Measurements for {self.ultrasound_image}"

class ThyroidUltrasoundMeasurements(BaseMeasurements):
    right_lobe_size = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text='cm')
    left_lobe_size = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text='cm')
    nodule_location = models.CharField(max_length=100, null=True, blank=True)
    nodule_size = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text='mm')

    def __str__(self):
        return f"Thyroid Measurements for {self.ultrasound_image}"

class UltrasoundExam(models.Model):
    RECOMMENDATION_CHOICES = [
        ('FI', 'Further imaging'),
        ('FU', 'Follow-up ultrasound'),
        ('RS', 'Referral to specialist'),
        ('BI', 'Biopsy/FNA advised'),
        ('NF', 'No further workup needed'),
    ]

    PLACENTA_GRADE_CHOICES = [
        ('0', 'Grade 0'),
        ('1', 'Grade I'),
        ('2', 'Grade II'),
        ('3', 'Grade III'),
    ]

    PLACENTA_LOCATION_CHOICES = [
        ('ANT', 'Anterior'),
        ('POS', 'Posterior'),
        ('FUN', 'Fundal'),
        ('LAT', 'Lateral'),
    ]

    FETAL_SEX_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('U', 'Undetermined'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='ultrasound_exams')
    referring_physician = models.CharField(max_length=100)
    clinical_diagnosis = models.TextField()
    medical_history = models.TextField()
    
    # Remove the old image field
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
    
    # Obstetric Ultrasound Specific Fields
    fetal_heart_rate = models.CharField(max_length=50, blank=True, null=True)
    amniotic_fluid = models.TextField(blank=True, null=True)
    placenta_location = models.CharField(max_length=3, choices=PLACENTA_LOCATION_CHOICES, blank=True, null=True)
    placenta_grade = models.CharField(max_length=1, choices=PLACENTA_GRADE_CHOICES, blank=True, null=True)
    fetal_sex = models.CharField(max_length=1, choices=FETAL_SEX_CHOICES, blank=True, null=True)
    edd = models.DateField(verbose_name="Estimated Date of Delivery", blank=True, null=True)
    efw = models.CharField(max_length=50, verbose_name="Estimated Fetal Weight", blank=True, null=True)
    
    # Billing Information
    or_number = models.CharField(max_length=50, blank=True, null=True)
    
    technologist_notes = models.TextField(blank=True, null=True)
    technologist_signature = models.CharField(max_length=100)
    radiologist_signature = models.CharField(max_length=100)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.patient.first_name} {self.patient.last_name} - {self.exam_date}"

    @property
    def placenta_description(self):
        if self.placenta_location and self.placenta_grade:
            location = dict(self.PLACENTA_LOCATION_CHOICES)[self.placenta_location]
            grade = dict(self.PLACENTA_GRADE_CHOICES)[self.placenta_grade]
            return f"{location} Placenta, {grade}"
        return None

    class Meta:
        ordering = ['-exam_date', '-exam_time'] 