from django import forms
from .models import Patient, UltrasoundExam
from billing.models import ServiceType

class PatientForm(forms.ModelForm):
    # Add help text for address fields
    region = forms.CharField(widget=forms.Select(attrs={
        'class': 'form-control',
        'id': 'id_region'
    }))
    province = forms.CharField(widget=forms.Select(attrs={
        'class': 'form-control',
        'id': 'id_province'
    }))
    city = forms.CharField(widget=forms.Select(attrs={
        'class': 'form-control',
        'id': 'id_city'
    }))
    barangay = forms.CharField(widget=forms.Select(attrs={
        'class': 'form-control',
        'id': 'id_barangay'
    }))

    class Meta:
        model = Patient
        fields = [
            'first_name', 'last_name', 'age', 'sex', 'date_of_birth', 'patient_type', 'id_number',
            'region', 'province', 'city', 'barangay', 'street_address',
            'contact_number', 'email', 'emergency_contact',
            'emergency_contact_number'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter first name',
                'pattern': '[A-Za-z ]+',
                'title': 'Only letters and spaces are allowed'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter last name',
                'pattern': '[A-Za-z ]+',
                'title': 'Only letters and spaces are allowed'
            }),
            'age': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter age'}),
            'sex': forms.Select(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'patient_type': forms.Select(attrs={'class': 'form-control', 'id': 'id_patient_type'}),
            'id_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter ID number'}),
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
        
        # Add help text
        self.fields['region'].help_text = 'Select your region'
        self.fields['province'].help_text = 'Select your province'
        self.fields['city'].help_text = 'Select your city/municipality'
        self.fields['barangay'].help_text = 'Select your barangay'

class UltrasoundExamForm(forms.ModelForm):
    class Meta:
        model = UltrasoundExam
        fields = [
            'patient', 'referring_physician', 'clinical_diagnosis', 'medical_history',
            'procedure_type', 'doppler_site', 'other_procedure',
            'exam_date', 'exam_time', 'technologist', 'radiologist',
            'findings', 'impression', 'recommendations', 'followup_duration',
            'specialist_referral', 'technologist_notes',
            'technologist_signature', 'radiologist_signature',
            'image'
        ]
        widgets = {
            'exam_date': forms.DateInput(attrs={'type': 'date'}),
            'exam_time': forms.TimeInput(attrs={'type': 'time'}),
            'clinical_diagnosis': forms.Textarea(attrs={'rows': 4}),
            'medical_history': forms.Textarea(attrs={'rows': 4}),
            'findings': forms.Textarea(attrs={'rows': 6}),
            'impression': forms.Textarea(attrs={'rows': 4}),
            'technologist_notes': forms.Textarea(attrs={'rows': 4}),
            'image': forms.FileInput(attrs={'accept': 'image/*', 'class': 'form-control'}),
            'procedure_type': forms.Select(attrs={'class': 'form-control'}),
            'recommendations': forms.Select(attrs={'class': 'form-control'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter only active service types
        self.fields['procedure_type'].queryset = ServiceType.objects.filter(is_active=True)
        self.fields['procedure_type'].empty_label = "Select a procedure type..." 