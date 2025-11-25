from django.db import models
from django.contrib.auth.models import User
from api.models.user import Tenant, UserProfile

class SupportTicket(models.Model):
    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent'),
    ]
    
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('IN_PROGRESS', 'In Progress'),
        ('WAITING_CUSTOMER', 'Waiting for Customer'),
        ('RESOLVED', 'Resolved'),
        ('CLOSED', 'Closed'),
    ]
    
    CATEGORY_CHOICES = [
        ('TECHNICAL', 'Technical Issue'),
        ('BILLING', 'Billing & Payment'),
        ('FEATURE', 'Feature Request'),
        ('ACCOUNT', 'Account Management'),
        ('GENERAL', 'General Inquiry'),
        ('BUG', 'Bug Report'),
    ]
    
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='support_tickets')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='support_tickets')
    
    # Ticket details
    ticket_number = models.CharField(max_length=20, unique=True)
    subject = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='MEDIUM')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    
    # Assignment
    assigned_to = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tickets')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    # SLA tracking
    due_date = models.DateTimeField(null=True, blank=True)
    response_time = models.DurationField(null=True, blank=True)
    resolution_time = models.DurationField(null=True, blank=True)
    
    # Tawk.to integration
    tawk_conversation_id = models.CharField(max_length=100, blank=True)
    tawk_visitor_id = models.CharField(max_length=100, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['priority', 'status']),
            models.Index(fields=['assigned_to', 'status']),
        ]
    
    def __str__(self):
        return f"#{self.ticket_number} - {self.subject}"
    
    def save(self, *args, **kwargs):
        if not self.ticket_number:
            self.ticket_number = self.generate_ticket_number()
        super().save(*args, **kwargs)
    
    def generate_ticket_number(self):
        """Generate unique ticket number"""
        import random
        import string
        from django.utils import timezone
        
        year = timezone.now().year
        random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"TKT-{year}-{random_suffix}"
    
    @property
    def is_overdue(self):
        """Check if ticket is overdue"""
        from django.utils import timezone
        if self.due_date and timezone.now() > self.due_date:
            return True
        return False
    
    @property
    def age_in_hours(self):
        """Get ticket age in hours"""
        from django.utils import timezone
        from datetime import timedelta
        
        age = timezone.now() - self.created_at
        return age.total_seconds() / 3600

class TicketResponse(models.Model):
    """Responses to support tickets"""
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='responses')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ticket_responses')
    
    message = models.TextField()
    is_internal = models.BooleanField(default=False)  # Internal note vs customer response
    created_at = models.DateTimeField(auto_now_add=True)
    
    # File attachments
    attachment = models.FileField(upload_to='ticket_attachments/', null=True, blank=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Response to #{self.ticket.ticket_number} by {self.user.username}"

class TicketSLA(models.Model):
    """SLA definitions for different ticket types"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='ticket_slas')
    
    category = models.CharField(max_length=20, choices=SupportTicket.CATEGORY_CHOICES)
    priority = models.CharField(max_length=20, choices=SupportTicket.PRIORITY_CHOICES)
    
    # Response time in hours
    first_response_hours = models.IntegerField()
    resolution_hours = models.IntegerField()
    
    # Escalation settings
    escalation_hours = models.IntegerField(null=True, blank=True)
    escalation_to = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['tenant', 'category', 'priority']
    
    def __str__(self):
        return f"{self.category} - {self.priority}: {self.first_response_hours}h response, {self.resolution_hours}h resolution"


class TicketCategory(models.Model):
    """Custom ticket categories (enhanced from basic choices)"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='ticket_categories')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#1976d2')  # Hex color
    icon = models.CharField(max_length=50, blank=True, help_text="Material icon name")
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ['tenant', 'name']
        ordering = ['order', 'name']
        verbose_name_plural = 'Ticket Categories'
    
    def __str__(self):
        return f"{self.name} ({self.tenant.name})"


class TicketPriority(models.Model):
    """Custom ticket priorities (enhanced from basic choices)"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='ticket_priorities')
    name = models.CharField(max_length=50)
    level = models.IntegerField(help_text="Priority level (1=Lowest, 5=Highest)")
    color = models.CharField(max_length=7, default='#1976d2')
    response_time_hours = models.IntegerField(help_text="Expected first response time in hours")
    resolution_time_hours = models.IntegerField(help_text="Expected resolution time in hours")
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['tenant', 'name']
        ordering = ['-level']
        verbose_name_plural = 'Ticket Priorities'
    
    def __str__(self):
        return f"{self.name} (Level {self.level}) ({self.tenant.name})"

class TawkToIntegration(models.Model):
    """Tawk.to integration settings"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='tawk_integration')
    
    # Tawk.to credentials
    site_id = models.CharField(max_length=100)
    widget_id = models.CharField(max_length=100)
    
    # Integration settings
    auto_create_tickets = models.BooleanField(default=True)
    ticket_category = models.CharField(max_length=20, choices=SupportTicket.CATEGORY_CHOICES, default='GENERAL')
    assign_to = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Chat settings
    welcome_message = models.TextField(blank=True)
    offline_message = models.TextField(blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['tenant']
    
    def __str__(self):
        return f"Tawk.to Integration for {self.tenant.name}" 