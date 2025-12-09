from django import forms
from .models import Patient, UltrasoundExam, Appointment
from billing.models import ServiceType
from django.contrib.auth.forms import PasswordChangeForm, UserChangeForm, UserChangeForm, UserCreationForm
from django.contrib.auth.models import User
from datetime import date, timedelta
import json
import os
from django.conf import settings

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
                'placeholder': 'Enter contact number',
                'type': 'tel',
                'pattern': '[0-9]{11}',
                'maxlength': '11',
                'title': 'Contact number must be exactly 11 digits (numbers only)'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter email address'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize empty choices for address dropdowns (JavaScript will load them)
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

        # Set required fields
        required_fields = ['first_name', 'last_name', 'birthday', 'sex', 'patient_type', 'patient_status', 'region', 'province', 'city', 'barangay', 'contact_number']
        for field in required_fields:
            self.fields[field].required = True

        # Set optional fields
        optional_fields = ['street_address', 'marital_status', 'id_number', 'email']
        for field in optional_fields:
            self.fields[field].required = False

    def clean_contact_number(self):
        contact_number = self.cleaned_data.get('contact_number')
        if contact_number:
            if not contact_number.isdigit():
                raise forms.ValidationError("Contact number must contain only digits.")
            if len(contact_number) != 11:
                raise forms.ValidationError("Contact number must be exactly 11 digits.")
        return contact_number

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
        fields = ['contact_number', 'email', 'street_address', 'profile_picture']
        widgets = {
            'contact_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter contact number',
                'type': 'tel',
                'pattern': '[0-9]{11}',
                'maxlength': '11',
                'title': 'Contact number must be exactly 11 digits (numbers only)'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter email address'
            }),
            'street_address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter street address, building name/number, etc.'
            }),
            'profile_picture': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
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
            'specialist_referral',
            'technician',
            'notes'
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

    procedure_type = forms.ChoiceField(
        widget=forms.Select(attrs={
            'class': 'form-control',
            'placeholder': 'Select procedure type'
        })
    )

    class Meta:
        model = Appointment
        fields = ['procedure_type', 'appointment_date', 'appointment_time', 'reason', 'notes', 'referral_image']
        widgets = {
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
            }),
            'referral_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*,.pdf',
                'required': 'required'  # Make it required in the form
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set minimum date to today
        self.fields['appointment_date'].widget.attrs['min'] = date.today().strftime('%Y-%m-%d')
        # Use ServiceType names with prices as choices for procedure_type
        self.fields['procedure_type'].choices = [('', '---')] + [(st.name, f"{st.name} - ₱{st.base_price}") for st in ServiceType.objects.filter(is_active=True)]
        # Set default to empty (which shows '---')
        self.initial['procedure_type'] = ''
        # Make referral_image required for new appointments
        self.fields['referral_image'].required = True

    def clean_referral_image(self):
        image = self.cleaned_data.get('referral_image')
        if image:
            # Check file size (5MB limit)
            if image.size > 5*1024*1024:
                raise forms.ValidationError("Image file too large (max 5MB)")
            
            # Check file extension
            valid_extensions = ['.jpg', '.jpeg', '.png', '.pdf']
            ext = os.path.splitext(image.name)[1].lower()
            if ext not in valid_extensions:
                raise forms.ValidationError("Unsupported file type. Use JPG, PNG, or PDF")
        
        return image
    
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

class StaffUserForm(forms.ModelForm):
    """Form for editing staff user information."""
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_staff', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter username'
            }),
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
            }),
            'is_staff': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add help text
        self.fields['username'].help_text = 'Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'
        self.fields['email'].help_text = 'Enter a valid email address.'

class StaffPasswordChangeForm(forms.Form):
    """Form for changing staff user password."""
    
    new_password1 = forms.CharField(
        label="New password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new password'
        }),
        help_text="Your password must contain at least 8 characters."
    )
    new_password2 = forms.CharField(
        label="Confirm new password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password'
        }),
        help_text="Enter the same password as before, for verification."
    )
    
    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
    
    def clean_new_password2(self):
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        
        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError("The two password fields didn't match.")
        
        return password2
    
    def save(self, commit=True):
        password = self.cleaned_data["new_password1"]
        self.user.set_password(password)
        if commit:
            self.user.save()
        return self.user 

class StaffUserCreationForm(forms.ModelForm):
    """Form for creating new staff users."""
    
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Enter password'
        }),
        help_text="Your password must contain at least 8 characters."
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Confirm password'
        }),
        help_text="Enter the same password as before, for verification."
    )
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Enter username'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Enter first name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Enter last name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Enter email address'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add help text
        self.fields['username'].help_text = 'Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'
        self.fields['email'].help_text = 'Enter a valid email address.'
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("A user with this username already exists.")
        return username
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email
    
    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        
        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError("The two password fields didn't match.")
            if len(password1) < 8:
                raise forms.ValidationError("Password must be at least 8 characters long.")
        
        return password2
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        user.is_staff = True
        user.is_active = True
        if commit:
            user.save()
        return user

from billing.models import ServiceType
class ServiceForm(forms.ModelForm):
    class Meta:
        model = ServiceType
        fields = ['name', 'description', 'base_price', 'is_active']

class PatientRegistrationForm(forms.Form):
    """Form for patient registration with user account creation."""
    
    # User account fields
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Choose a username',
            'pattern': '[A-Za-z0-9@/./+/-/_]+',
            'title': 'Letters, digits and @/./+/-/_ only'
        }),
        help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'
    )
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter password'
        }),
        help_text='Your password must contain at least 8 characters.'
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm password'
        }),
        help_text='Enter the same password as before, for verification.'
    )
    
    # Patient information fields
    first_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter first name',
            'pattern': '[A-Za-z ]+',
            'title': 'Only letters and spaces are allowed'
        })
    )
    last_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter last name',
            'pattern': '[A-Za-z ]+',
            'title': 'Only letters and spaces are allowed'
        })
    )
    birthday = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'placeholder': 'Select birthday'
        })
    )
    sex = forms.ChoiceField(
        choices=Patient.GENDER_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    marital_status = forms.ChoiceField(
        choices=Patient.MARITAL_STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    patient_type = forms.ChoiceField(
        choices=Patient.PATIENT_TYPE_CHOICES,
        initial='REGULAR',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    id_number = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter Senior Citizen/PWD ID number'
        })
    )
    
    # Address fields
    region = forms.CharField(
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'id_region'
        })
    )
    province = forms.CharField(
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'id_province',
            'disabled': True
        })
    )
    city = forms.CharField(
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'id_city',
            'disabled': True
        })
    )
    barangay = forms.CharField(
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'id_barangay',
            'disabled': True
        })
    )
    street_address = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Enter street address, building name/number, etc.'
        })
    )
    
    # Contact information
    contact_number = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter contact number',
            'type': 'tel',
            'pattern': '[0-9]{11}',
            'maxlength': '11',
            'title': 'Contact number must be exactly 11 digits (numbers only)'
        })
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter email address'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize empty choices for address dropdowns
        self.fields['region'].choices = [('', 'Select Region...')]
        self.fields['province'].choices = [('', 'Select Province...')]
        self.fields['city'].choices = [('', 'Select City/Municipality...')]
        self.fields['barangay'].choices = [('', 'Select Barangay...')]
        
        # Add help text for address fields
        self.fields['region'].help_text = 'Select your region'
        self.fields['province'].help_text = 'Select your province'
        self.fields['city'].help_text = 'Select your city/municipality'
        self.fields['barangay'].help_text = 'Select your barangay'
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("A user with this username already exists.")
        return username
    
    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        
        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError("The two password fields didn't match.")
        
        return password2
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email
    
    def clean_contact_number(self):
        contact_number = self.cleaned_data.get('contact_number')
        if contact_number:
            if not contact_number.isdigit():
                raise forms.ValidationError("Contact number must contain only digits.")
            if len(contact_number) != 11:
                raise forms.ValidationError("Contact number must be exactly 11 digits.")
        if Patient.objects.filter(contact_number=contact_number).exists():
            raise forms.ValidationError("A patient with this contact number already exists.")
        return contact_number
