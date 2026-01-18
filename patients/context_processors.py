def elevation_context(request):
    """
    Context processor to provide elevation status to all templates.
    This allows templates to conditionally show admin features based on temporary elevation.
    """
    return {
        'is_elevated_admin': request.session.get('elevated_admin', False),
        'original_user_id': request.session.get('_original_user_id'),
    }

def staff_notifications_context(request):
    """
    Context processor to provide new appointments for staff notifications.
    Only for staff (not superusers).
    """
    if request.user.is_authenticated and request.user.is_staff and not request.user.is_superuser:
        from django.utils import timezone
        from datetime import timedelta
        from .models import Appointment
        
        # Get new appointments (created in last 7 days, status PENDING)
        seven_days_ago = timezone.now() - timedelta(days=7)
        new_appointments = list(Appointment.objects.filter(
            created_at__gte=seven_days_ago,
            status='PENDING'
        ).select_related('patient').order_by('-created_at')[:10])
        
        return {
            'new_appointments': new_appointments,
            'new_appointments_count': len(new_appointments),
        }
    return {
        'new_appointments': [],
        'new_appointments_count': 0,
    }


def patient_notifications_context(request):
    """
    Context processor to provide notification data for patient templates.
    This ensures the notification bell works on all patient pages (appointments, bills, settings, etc.)
    """
    if request.user.is_authenticated and hasattr(request.user, 'patient'):
        from django.utils import timezone
        from datetime import timedelta
        from .models import Appointment
        
        patient = request.user.patient
        now = timezone.now()
        
        # Get confirmed appointments for notifications
        confirmed_appointments = list(Appointment.objects.filter(
            patient=patient,
            status='CONFIRMED',
            appointment_date__gte=now.date()  # Only future confirmed appointments
        ).order_by('appointment_date', 'appointment_time')[:10])
        
        # Get upcoming appointments (within next 24 hours) - only PENDING to avoid double counting
        tomorrow = now + timedelta(days=1)
        upcoming_appointments = list(Appointment.objects.filter(
            patient=patient,
            appointment_date__gte=now.date(),
            appointment_date__lte=tomorrow.date(),
            status='PENDING'  # Only PENDING to avoid double counting with confirmed
        ).order_by('appointment_date', 'appointment_time'))
        
        # Calculate total unique notifications
        total_notifications = len(confirmed_appointments) + len(upcoming_appointments)
        
        return {
            'confirmed_appointments': confirmed_appointments,
            'upcoming_appointments': upcoming_appointments,
            'total_notifications': total_notifications,
        }
    return {
        'confirmed_appointments': [],
        'upcoming_appointments': [],
        'total_notifications': 0,
    }
