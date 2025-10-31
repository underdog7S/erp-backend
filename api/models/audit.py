"""
Audit logging model for security and compliance
"""
from django.db import models
from django.contrib.auth.models import User
from api.models.user import UserProfile

class AuditLog(models.Model):
    """
    Audit log for tracking all important user actions
    """
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('PASSWORD_CHANGE', 'Password Change'),
        ('PASSWORD_RESET', 'Password Reset'),
        ('PERMISSION_DENIED', 'Permission Denied'),
        ('FILE_UPLOAD', 'File Upload'),
        ('FILE_DOWNLOAD', 'File Download'),
        ('EXPORT', 'Export'),
        ('IMPORT', 'Import'),
        ('VIEW', 'View'),
        ('OTHER', 'Other'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    user_profile = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    resource_type = models.CharField(max_length=100, help_text="Type of resource (e.g., Student, Payment, User)")
    resource_id = models.IntegerField(null=True, blank=True, help_text="ID of the affected resource")
    resource_name = models.CharField(max_length=255, blank=True, help_text="Name/identifier of the resource")
    
    # Request details
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    request_method = models.CharField(max_length=10, blank=True)
    request_path = models.CharField(max_length=500, blank=True)
    
    # Request/Response data (stored as JSON for flexibility)
    request_data = models.JSONField(null=True, blank=True, help_text="Sanitized request data")
    response_status = models.IntegerField(null=True, blank=True)
    
    # Additional context
    description = models.TextField(blank=True, help_text="Human-readable description of the action")
    success = models.BooleanField(default=True, help_text="Whether the action was successful")
    error_message = models.TextField(blank=True, help_text="Error message if action failed")
    
    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'action']),
            models.Index(fields=['resource_type', 'resource_id']),
            models.Index(fields=['ip_address']),
            models.Index(fields=['created_at']),
            models.Index(fields=['action', 'created_at']),
        ]
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
    
    def __str__(self):
        user_str = self.user.username if self.user else 'Anonymous'
        return f"{user_str} - {self.action} - {self.resource_type} ({self.created_at})"
    
    @classmethod
    def log_action(cls, request, action, resource_type, resource_id=None, resource_name=None, 
                   success=True, description='', error_message='', request_data=None):
        """
        Convenience method to create an audit log entry
        """
        user = request.user if hasattr(request, 'user') and request.user.is_authenticated else None
        user_profile = None
        
        if user:
            try:
                user_profile = UserProfile._default_manager.get(user=user)
            except UserProfile.DoesNotExist:
                pass
        
        # Get IP address
        ip_address = None
        if hasattr(request, 'META'):
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0].strip()
            else:
                ip_address = request.META.get('REMOTE_ADDR')
        
        # Get user agent
        user_agent = request.META.get('HTTP_USER_AGENT', '') if hasattr(request, 'META') else ''
        
        # Sanitize request data (remove sensitive fields)
        sanitized_data = None
        if request_data:
            sanitized_data = cls.sanitize_request_data(request_data)
        
        return cls.objects.create(
            user=user,
            user_profile=user_profile,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            ip_address=ip_address,
            user_agent=user_agent,
            request_method=getattr(request, 'method', ''),
            request_path=getattr(request, 'path', ''),
            request_data=sanitized_data,
            success=success,
            description=description,
            error_message=error_message
        )
    
    @staticmethod
    def sanitize_request_data(data):
        """
        Remove sensitive information from request data before logging
        """
        if not isinstance(data, dict):
            return None
        
        sensitive_fields = ['password', 'token', 'secret', 'key', 'authorization', 'csrfmiddlewaretoken']
        sanitized = {}
        
        for key, value in data.items():
            if any(field in key.lower() for field in sensitive_fields):
                sanitized[key] = '[REDACTED]'
            elif isinstance(value, dict):
                sanitized[key] = AuditLog.sanitize_request_data(value)
            elif isinstance(value, list):
                sanitized[key] = [AuditLog.sanitize_request_data(item) if isinstance(item, dict) else item for item in value]
            else:
                sanitized[key] = value
        
        return sanitized

