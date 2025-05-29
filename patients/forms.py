from django import forms
from .models import Patient, UltrasoundExam

class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = [
            'name', 'age', 'sex', 'date_of_birth',
            'region', 'province', 'city', 'barangay', 'street_address',
            'contact_number', 'email', 'emergency_contact',
            'emergency_contact_number'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter full name'}),
            'age': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter age'}),
            'sex': forms.Select(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'region': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_region'
            }),
            'province': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_province'
            }),
            'city': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_city'
            }),
            'barangay': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_barangay'
            }),
            'street_address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter street address, building name/number, etc.'
            }),
            'contact_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter contact number'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter email address'
            }),
            'emergency_contact': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter emergency contact name'
            }),
            'emergency_contact_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter emergency contact number'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize empty choices for address dropdowns
        self.fields['region'].choices = [('', 'Select Region...')]
        self.fields['province'].choices = [('', 'Select Province...')]
        self.fields['city'].choices = [('', 'Select City/Municipality...')]
        self.fields['barangay'].choices = [('', 'Select Barangay...')]
        
        # Disable cascading fields initially
        self.fields['province'].widget.attrs['disabled'] = True
        self.fields['city'].widget.attrs['disabled'] = True
        self.fields['barangay'].widget.attrs['disabled'] = True

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