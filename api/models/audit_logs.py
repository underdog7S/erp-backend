from django.db import models
from django.contrib.auth.models import User
from api.models.user import Tenant

class AuditLog(models.Model):
    ACTION_TYPES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('VIEW', 'View'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('OTHER', 'Other'),
    ]

    RESOURCE_TYPES = [
        ('MANUFACTURING', 'Manufacturing'),
        ('EDUCATION', 'Education'),
        ('HEALTHCARE', 'Healthcare'),
        ('USERS', 'Users'),
        ('PLANS', 'Plans'),
        ('PAYMENTS', 'Payments'),
        ('UNKNOWN', 'Unknown'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='audit_logs')
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True, related_name='audit_logs')
    
    # Action details
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES)
    resource_type = models.CharField(max_length=20, choices=RESOURCE_TYPES)
    resource_id = models.IntegerField(null=True, blank=True)
    
    # Request details
    request_method = models.CharField(max_length=10)
    request_path = models.CharField(max_length=255)
    request_data = models.JSONField(default=dict, blank=True)
    response_status = models.IntegerField()
    
    # User context
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['tenant', 'timestamp']),
            models.Index(fields=['action_type', 'timestamp']),
            models.Index(fields=['resource_type', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.action_type} - {self.resource_type} - {self.timestamp}"

    @classmethod
    def get_user_activity(cls, user, days=30):
        """Get user activity for the last N days"""
        from django.utils import timezone
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=days)
        return cls.objects.filter(user=user, timestamp__gte=cutoff_date)

    @classmethod
    def get_tenant_activity(cls, tenant, days=30):
        """Get tenant activity for the last N days"""
        from django.utils import timezone
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=days)
        return cls.objects.filter(tenant=tenant, timestamp__gte=cutoff_date)

    @classmethod
    def get_resource_activity(cls, resource_type, resource_id=None, days=30):
        """Get activity for a specific resource"""
        from django.utils import timezone
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=days)
        queryset = cls.objects.filter(resource_type=resource_type, timestamp__gte=cutoff_date)
        
        if resource_id:
            queryset = queryset.filter(resource_id=resource_id)
            
        return queryset 