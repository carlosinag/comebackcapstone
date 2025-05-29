from django import forms
from .models import Patient, UltrasoundExam

class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = [
            'name', 'age', 'sex', 'date_of_birth', 'address', 
            'contact_number', 'email', 'emergency_contact', 
            'emergency_contact_number'
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }

class UltrasoundExamForm(forms.ModelForm):
    class Meta:
        model = UltrasoundExam
        fields = [
            'patient', 'referring_physician', 'clinical_diagnosis', 'medical_history',
            'procedure_type', 'doppler_site', 'other_procedure',
            'exam_date', 'exam_time', 'technologist', 'radiologist',
            'findings', 'impression', 'recommendations', 'followup_duration',
            'specialist_referral', 'technologist_notes',
            'technologist_signature', 'radiologist_signature'
        ]
        widgets = {
            'exam_date': forms.DateInput(attrs={'type': 'date'}),
            'exam_time': forms.TimeInput(attrs={'type': 'time'}),
            'clinical_diagnosis': forms.Textarea(attrs={'rows': 4}),
            'medical_history': forms.Textarea(attrs={'rows': 4}),
            'findings': forms.Textarea(attrs={'rows': 6}),
            'impression': forms.Textarea(attrs={'rows': 4}),
            'technologist_notes': forms.Textarea(attrs={'rows': 4}),
        } 