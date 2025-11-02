"""
Utility functions for creating and managing notifications
"""
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from typing import Optional, Dict, Any

from api.models.user import Tenant
from api.models.notifications import Notification, NotificationPreference


def create_notification(
    user: User,
    tenant: Tenant,
    title: str,
    message: str,
    notification_type: str = 'info',
    module: str = 'general',
    priority: str = 'medium',
    action_url: Optional[str] = None,
    action_label: Optional[str] = None,
    reference_type: Optional[str] = None,
    reference_id: Optional[int] = None,
    icon: Optional[str] = None,
    expires_in_days: Optional[int] = None
) -> Notification:
    """
    Create a new notification for a user
    
    Args:
        user: User to notify
        tenant: Tenant/organization
        title: Notification title
        message: Notification message
        notification_type: Type of notification (info, success, warning, error, reminder, announcement, alert)
        module: Module name (education, pharmacy, retail, etc.)
        priority: Priority level (low, medium, high, urgent)
        action_url: Optional URL for action button
        action_label: Optional label for action button
        reference_type: Type of referenced object (e.g., 'Student', 'Sale')
        reference_id: ID of referenced object
        icon: Icon name or emoji
        expires_in_days: Number of days until notification expires
    
    Returns:
        Created Notification object
    """
    expires_at = None
    if expires_in_days:
        expires_at = timezone.now() + timedelta(days=expires_in_days)
    
    notification = Notification.objects.create(
        user=user,
        tenant=tenant,
        title=title,
        message=message,
        notification_type=notification_type,
        module=module,
        priority=priority,
        action_url=action_url,
        action_label=action_label,
        reference_type=reference_type,
        reference_id=reference_id,
        icon=icon,
        expires_at=expires_at
    )
    
    # Log in-app delivery
    from api.models.notifications import NotificationLog
    NotificationLog.objects.create(
        notification=notification,
        delivery_method='in_app',
        status='sent'
    )
    
    # TODO: Send email/SMS based on user preferences
    # _send_notification_channels(notification)
    
    return notification


def create_bulk_notification(
    users: list,
    tenant: Tenant,
    title: str,
    message: str,
    notification_type: str = 'info',
    module: str = 'general',
    priority: str = 'medium',
    **kwargs
) -> list:
    """
    Create notifications for multiple users
    
    Returns:
        List of created Notification objects
    """
    notifications = []
    for user in users:
        notification = create_notification(
            user=user,
            tenant=tenant,
            title=title,
            message=message,
            notification_type=notification_type,
            module=module,
            priority=priority,
            **kwargs
        )
        notifications.append(notification)
    
    return notifications


def create_module_notification(
    user: User,
    tenant: Tenant,
    module: str,
    title: str,
    message: str,
    notification_type: str = 'info',
    **kwargs
) -> Notification:
    """
    Convenience function to create a module-specific notification
    """
    return create_notification(
        user=user,
        tenant=tenant,
        title=title,
        message=message,
        notification_type=notification_type,
        module=module,
        **kwargs
    )


# Module-specific helper functions

def notify_fee_payment(user: User, tenant: Tenant, student_name: str, amount: float, **kwargs):
    """Create notification for fee payment"""
    return create_module_notification(
        user=user,
        tenant=tenant,
        module='education',
        title='Fee Payment Received',
        message=f'Payment of ₹{amount:.2f} received for {student_name}.',
        notification_type='success',
        icon='payments',
        **kwargs
    )


def notify_low_stock(user: User, tenant: Tenant, product_name: str, current_stock: int, module: str = 'retail', **kwargs):
    """Create notification for low stock"""
    return create_module_notification(
        user=user,
        tenant=tenant,
        module=module,
        title='Low Stock Alert',
        message=f'{product_name} is running low. Current stock: {current_stock}',
        notification_type='warning',
        priority='high',
        icon='inventory',
        **kwargs
    )


def notify_new_booking(user: User, tenant: Tenant, booking_details: Dict[str, Any], module: str = 'salon', **kwargs):
    """Create notification for new booking"""
    return create_module_notification(
        user=user,
        tenant=tenant,
        module=module,
        title='New Booking',
        message=f'New booking received: {booking_details.get("service_name", "Service")}',
        notification_type='info',
        icon='event',
        **kwargs
    )


def notify_appointment_reminder(user: User, tenant: Tenant, appointment_details: Dict[str, Any], **kwargs):
    """Create reminder notification"""
    return create_module_notification(
        user=user,
        tenant=tenant,
        module='salon',
        title='Appointment Reminder',
        message=f'You have an appointment scheduled for {appointment_details.get("date")}',
        notification_type='reminder',
        priority='medium',
        icon='alarm',
        **kwargs
    )


def cleanup_expired_notifications(days_old: int = 30):
    """
    Clean up old expired notifications
    
    Args:
        days_old: Delete notifications older than this many days
    """
    cutoff_date = timezone.now() - timedelta(days=days_old)
    deleted_count = Notification.objects.filter(
        created_at__lt=cutoff_date
    ).delete()[0]
    
    return deleted_count


def get_user_unread_count(user: User) -> int:
    """Get count of unread notifications for a user"""
    return Notification.objects.filter(
        user=user,
        read=False
    ).exclude(
        expires_at__lt=timezone.now()
    ).count()

