from django.db import models
from django.contrib.auth.models import User
from api.models.user import Tenant, UserProfile

class Notification(models.Model):
    """
    Comprehensive notification system for user-specific notifications across all modules.
    Extends the Alert system to provide module-specific, user-targeted notifications.
    """
    NOTIFICATION_TYPES = [
        ('info', 'Information'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('reminder', 'Reminder'),
        ('announcement', 'Announcement'),
        ('alert', 'Alert'),
    ]
    
    MODULE_CHOICES = [
        ('education', 'Education'),
        ('pharmacy', 'Pharmacy'),
        ('retail', 'Retail'),
        ('hotel', 'Hotel'),
        ('restaurant', 'Restaurant'),
        ('salon', 'Salon'),
        ('general', 'General'),
        ('system', 'System'),
    ]
    
    PRIORITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    # Core fields
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='tenant_notifications')
    
    # Notification content
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='info')
    module = models.CharField(max_length=50, choices=MODULE_CHOICES, default='general')
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='medium')
    
    # Action/Reference
    action_url = models.URLField(null=True, blank=True, help_text="Link to related page/resource")
    action_label = models.CharField(max_length=100, null=True, blank=True, help_text="Text for action button")
    reference_type = models.CharField(max_length=50, null=True, blank=True, help_text="e.g., 'Student', 'Sale', 'Booking'")
    reference_id = models.IntegerField(null=True, blank=True, help_text="ID of the referenced object")
    
    # Status
    read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Delivery status (for future email/SMS integration)
    email_sent = models.BooleanField(default=False)
    sms_sent = models.BooleanField(default=False)
    push_sent = models.BooleanField(default=False)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Auto-hide after this date")
    
    # Icon/Image
    icon = models.CharField(max_length=50, null=True, blank=True, help_text="Material icon name or emoji")
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'read', 'created_at']),
            models.Index(fields=['tenant', 'module', 'created_at']),
            models.Index(fields=['user', 'notification_type']),
        ]
    
    def __str__(self):
        return f"{self.user.username}: {self.title} ({self.notification_type})"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.read:
            self.read = True
            from django.utils import timezone
            self.read_at = timezone.now()
            self.save(update_fields=['read', 'read_at'])
    
    def is_expired(self):
        """Check if notification has expired"""
        if self.expires_at:
            from django.utils import timezone
            return timezone.now() > self.expires_at
        return False


class NotificationPreference(models.Model):
    """
    User preferences for notifications - controls how notifications are delivered
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_preferences')
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    
    # Delivery channels
    email_enabled = models.BooleanField(default=True, help_text="Send notifications via email")
    sms_enabled = models.BooleanField(default=False, help_text="Send notifications via SMS")
    push_enabled = models.BooleanField(default=True, help_text="Show browser push notifications")
    in_app_enabled = models.BooleanField(default=True, help_text="Show in-app notifications")
    
    # Module-specific preferences (JSON field for flexibility)
    module_preferences = models.JSONField(
        default=dict,
        help_text="Per-module preferences, e.g., {'education': {'email': True, 'sms': False}}"
    )
    
    # Type-specific preferences
    type_preferences = models.JSONField(
        default=dict,
        help_text="Per-type preferences, e.g., {'reminder': {'email': True}, 'alert': {'sms': True}}"
    )
    
    # Quiet hours
    quiet_hours_start = models.TimeField(null=True, blank=True, help_text="Don't send notifications after this time")
    quiet_hours_end = models.TimeField(null=True, blank=True, help_text="Resume notifications after this time")
    
    # Frequency limits
    max_emails_per_day = models.IntegerField(default=50, help_text="Maximum email notifications per day")
    max_sms_per_day = models.IntegerField(default=10, help_text="Maximum SMS notifications per day")
    
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Notification preferences for {self.user.username}"


class NotificationTemplate(models.Model):
    """
    Templates for different notification types - allows customization of notification messages
    """
    name = models.CharField(max_length=100, unique=True)
    module = models.CharField(max_length=50, choices=Notification.MODULE_CHOICES, default='general')
    notification_type = models.CharField(max_length=20, choices=Notification.NOTIFICATION_TYPES)
    
    # Template content
    title_template = models.CharField(max_length=200, help_text="Template for notification title, use {variables}")
    message_template = models.TextField(help_text="Template for notification message, use {variables}")
    
    # Template variables
    variables = models.JSONField(
        default=list,
        help_text="List of available variables, e.g., ['student_name', 'class_name', 'amount']"
    )
    
    # Default settings
    default_priority = models.CharField(max_length=10, choices=Notification.PRIORITY_LEVELS, default='medium')
    default_icon = models.CharField(max_length=50, null=True, blank=True)
    default_expiry_days = models.IntegerField(null=True, blank=True, help_text="Auto-expire after N days")
    
    # Email/SMS templates
    email_subject_template = models.CharField(max_length=200, null=True, blank=True)
    email_body_template = models.TextField(null=True, blank=True)
    sms_template = models.CharField(max_length=160, null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.module}/{self.notification_type})"


class NotificationLog(models.Model):
    """
    Log of notification delivery attempts - useful for debugging and analytics
    """
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name='delivery_logs')
    delivery_method = models.CharField(max_length=20, choices=[
        ('in_app', 'In-App'),
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Push Notification'),
    ])
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('bounced', 'Bounced'),
    ])
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.notification.title} via {self.delivery_method} - {self.status}"

