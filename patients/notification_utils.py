import asyncio
import threading
from .consumers import send_notification_to_user
from .models import Notification
from django.contrib.auth.models import User

def send_notification_sync(user_id, notification_type, title, message, appointment_id=None):
    """
    Synchronous wrapper for sending notifications.
    Creates a notification in the database and sends it via WebSocket.
    """
    # Create notification in database
    notification = Notification.objects.create(
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        message=message,
        appointment_id=appointment_id
    )
    
    # Send via WebSocket in a separate thread
    def run_async_notification():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(send_notification_to_user(
                user_id=user_id,
                notification_type=notification_type,
                title=title,
                message=message,
                appointment_id=appointment_id
            ))
        finally:
            loop.close()
    
    thread = threading.Thread(target=run_async_notification)
    thread.start()
    
    return notification

def notify_staff_new_appointment(appointment):
    """
    Send notification to all staff members about a new appointment.
    """
    staff_users = User.objects.filter(is_staff=True, is_superuser=False)
    
    for staff_user in staff_users:
        send_notification_sync(
            user_id=staff_user.id,
            notification_type='APPOINTMENT_BOOKED',
            title='New Appointment Booked',
            message=f'{appointment.patient.first_name} {appointment.patient.last_name} booked a {appointment.get_procedure_type_display()} appointment for {appointment.appointment_date} at {appointment.appointment_time}',
            appointment_id=appointment.id
        )

def notify_patient_appointment_update(appointment, action):
    """
    Send notification to patient about appointment status change.
    """
    if action == 'confirmed':
        notification_type = 'APPOINTMENT_CONFIRMED'
        title = 'Appointment Confirmed'
        message = f'Your {appointment.get_procedure_type_display()} appointment on {appointment.appointment_date} at {appointment.appointment_time} has been confirmed.'
    elif action == 'cancelled':
        notification_type = 'APPOINTMENT_CANCELLED'
        title = 'Appointment Cancelled'
        message = f'Your {appointment.get_procedure_type_display()} appointment on {appointment.appointment_date} at {appointment.appointment_time} has been cancelled.'
    else:
        return
    
    send_notification_sync(
        user_id=appointment.patient.user.id,
        notification_type=notification_type,
        title=title,
        message=message,
        appointment_id=appointment.id
    )
