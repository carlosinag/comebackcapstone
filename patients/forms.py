from django import forms
from .models import Patient, UltrasoundExam, Appointment
from billing.models import ServiceType
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from datetime import date, timedelta

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
            'first_name', 'last_name', 'birthday', 'sex', 'marital_status',
            'patient_type', 'patient_status', 'id_number',
            'region', 'province', 'city', 'barangay', 'street_address',
            'contact_number', 'email'
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
            'birthday': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'placeholder': 'Select birthday'}),
            'sex': forms.Select(attrs={'class': 'form-control'}),
            'marital_status': forms.Select(attrs={'class': 'form-control'}),
            'patient_type': forms.Select(attrs={'class': 'form-control', 'id': 'id_patient_type'}),
            'patient_status': forms.Select(attrs={'class': 'form-control', 'id': 'id_patient_status'}),
            'id_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter Senior Citizen/PWD ID number'
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
            })
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

class PatientPasswordChangeForm(PasswordChangeForm):
    """Custom password change form for patients with Bootstrap styling."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})

class PatientProfileForm(forms.ModelForm):
    """Form for patients to update their profile information."""
    
    class Meta:
        model = Patient
        fields = ['contact_number', 'email', 'street_address']
        widgets = {
            'contact_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter contact number'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter email address'
            }),
            'street_address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter street address, building name/number, etc.'
            })
        }

class PatientUserForm(forms.ModelForm):
    """Form for patients to update their user account information."""
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter first name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter last name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter email address'
            })
        }

class UltrasoundExamForm(forms.ModelForm):
    class Meta:
        model = UltrasoundExam
        fields = [
            'patient',
            'referring_physician',
            'procedure_type',
            'exam_date',
            'exam_time',
            'findings',
            'impression',
            'recommendations',
            'followup_duration',
            'specialist_referral'
        ]
        widgets = {
            'exam_date': forms.DateInput(attrs={'type': 'date'}),
            'exam_time': forms.TimeInput(attrs={'type': 'time'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter only active service types
        self.fields['procedure_type'].queryset = ServiceType.objects.filter(is_active=True)
        self.fields['procedure_type'].empty_label = "Select a procedure type..." 

class AppointmentForm(forms.ModelForm):
    """Form for patients to book appointments."""
    
    class Meta:
        model = Appointment
        fields = ['procedure_type', 'appointment_date', 'appointment_time', 'reason', 'notes']
        widgets = {
            'procedure_type': forms.Select(attrs={
                'class': 'form-control',
                'placeholder': 'Select procedure type'
            }),
            'appointment_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'min': date.today().strftime('%Y-%m-%d')
            }),
            'appointment_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Please describe your symptoms or reason for the appointment'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Any additional notes or special requirements'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set minimum date to today
        self.fields['appointment_date'].widget.attrs['min'] = date.today().strftime('%Y-%m-%d')
    
    def clean_appointment_date(self):
        appointment_date = self.cleaned_data.get('appointment_date')
        if appointment_date and appointment_date < date.today():
            raise forms.ValidationError("Appointment date cannot be in the past.")
        return appointment_date
    
    def clean_appointment_time(self):
        appointment_time = self.cleaned_data.get('appointment_time')
        appointment_date = self.cleaned_data.get('appointment_date')
        
        if appointment_date and appointment_time:
            # Check if appointment is within clinic hours (8 AM to 5 PM)
            if appointment_time < appointment_time.replace(hour=8, minute=0) or appointment_time > appointment_time.replace(hour=17, minute=0):
                raise forms.ValidationError("Appointments are only available between 8:00 AM and 5:00 PM.")
        
        return appointment_time

class AppointmentUpdateForm(forms.ModelForm):
    """Form for patients to update their appointments."""
    
    class Meta:
        model = Appointment
        fields = ['appointment_date', 'appointment_time', 'reason', 'notes']
        widgets = {
            'appointment_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'appointment_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Please describe your symptoms or reason for the appointment'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Any additional notes or special requirements'
            })
        }
    
    def clean_appointment_date(self):
        appointment_date = self.cleaned_data.get('appointment_date')
        if appointment_date and appointment_date < date.today():
            raise forms.ValidationError("Appointment date cannot be in the past.")
        return appointment_date 