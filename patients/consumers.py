import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import Notification, Appointment
from asgiref.sync import sync_to_async

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.room_group_name = f'notifications_{self.user_id}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send unread notifications count on connect
        unread_count = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': unread_count
        }))

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json.get('type')
        
        if message_type == 'mark_read':
            notification_id = text_data_json.get('notification_id')
            await self.mark_notification_read(notification_id)
        elif message_type == 'get_notifications':
            notifications = await self.get_recent_notifications()
            await self.send(text_data=json.dumps({
                'type': 'notifications_list',
                'notifications': notifications
            }))

    # Receive message from room group
    async def notification_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'title': event['title'],
            'message': event['message'],
            'notification_type': event['notification_type'],
            'appointment_id': event.get('appointment_id'),
            'created_at': event['created_at']
        }))
        
        # Update unread count
        unread_count = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': unread_count
        }))

    @database_sync_to_async
    def get_unread_count(self):
        try:
            user = User.objects.get(id=self.user_id)
            return Notification.objects.filter(user=user, is_read=False).count()
        except User.DoesNotExist:
            return 0

    @database_sync_to_async
    def get_recent_notifications(self):
        try:
            user = User.objects.get(id=self.user_id)
            notifications = Notification.objects.filter(user=user).order_by('-created_at')[:10]
            return [
                {
                    'id': notification.id,
                    'title': notification.title,
                    'message': notification.message,
                    'notification_type': notification.notification_type,
                    'is_read': notification.is_read,
                    'appointment_id': notification.appointment.id if notification.appointment else None,
                    'created_at': notification.created_at.isoformat()
                }
                for notification in notifications
            ]
        except User.DoesNotExist:
            return []

    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        try:
            notification = Notification.objects.get(id=notification_id, user_id=self.user_id)
            notification.is_read = True
            notification.save()
        except Notification.DoesNotExist:
            pass

# Utility function to send notifications
async def send_notification_to_user(user_id, notification_type, title, message, appointment_id=None):
    from channels.layers import get_channel_layer
    from django.utils import timezone
    
    channel_layer = get_channel_layer()
    room_group_name = f'notifications_{user_id}'
    
    await channel_layer.group_send(
        room_group_name,
        {
            'type': 'notification_message',
            'title': title,
            'message': message,
            'notification_type': notification_type,
            'appointment_id': appointment_id,
            'created_at': timezone.now().isoformat()
        }
    )

# Utility function to create and send notification
async def create_and_send_notification(user_id, notification_type, title, message, appointment_id=None):
    from .models import Notification
    
    # Create notification in database
    notification = await sync_to_async(Notification.objects.create)(
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        message=message,
        appointment_id=appointment_id
    )
    
    # Send real-time notification
    await send_notification_to_user(user_id, notification_type, title, message, appointment_id)
    
    return notification
