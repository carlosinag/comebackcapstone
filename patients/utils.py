import random
import string
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

def send_appointment_accepted_email(appointment):
    """Send an email notification to the patient when appointment is accepted (confirmed)."""
    patient = appointment.patient
    if not patient.email:
        return  # No email to send to

    subject = "Your Appointment Has Been Accepted"
    email_context = {
        "patient_name": f"{patient.first_name} {patient.last_name}",
        "appointment_date": appointment.appointment_date,
        "appointment_time": appointment.appointment_time,
        "procedure_type": appointment.procedure_type,
    }
    html_content = render_to_string("emails/appointment_accepted.html", email_context)
    text_content = (
        f"Dear {email_context['patient_name']},\n\n"
        f"Your appointment for {email_context['procedure_type']} on "
        f"{email_context['appointment_date']} at {email_context['appointment_time']} has been accepted.\n\n"
        "Thank you for booking with us."
    )
    try:
        msg = EmailMultiAlternatives(
            subject,
            text_content,
            settings.DEFAULT_FROM_EMAIL,
            [patient.email],
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=True)
    except Exception:
        # Fail quietly; optionally log error
        pass

def generate_username(first_name, last_name):
    """Generate a unique username based on patient's name."""
    base_username = f"{first_name.lower()}{last_name.lower()}"
    username = base_username
    counter = 1
    
    while User.objects.filter(username=username).exists():
        username = f"{base_username}{counter}"
        counter += 1
    
    return username

def generate_password():
    """Generate a secure random password."""
    # Define character sets
    letters = string.ascii_letters
    digits = string.digits
    special_chars = "!@#$%^&*"
    
    # Ensure at least one of each type
    password = [
        random.choice(letters.upper()),
        random.choice(letters.lower()),
        random.choice(digits),
        random.choice(special_chars)
    ]
    
    # Fill rest with random characters
    for _ in range(8):  # Add 8 more characters
        password.append(random.choice(letters + digits + special_chars))
    
    # Shuffle the password characters
    random.shuffle(password)
    
    return ''.join(password) 