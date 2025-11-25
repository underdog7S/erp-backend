from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from api.models.user import Tenant, UserProfile


class EmailTemplate(models.Model):
    """Reusable email templates"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='email_templates')
    name = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    body_html = models.TextField(help_text="HTML email body")
    body_text = models.TextField(blank=True, help_text="Plain text version")
    
    # Template variables (e.g., {{first_name}}, {{company_name}})
    variables = models.JSONField(
        default=list,
        blank=True,
        help_text="List of available variables in this template"
    )
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='created_email_templates')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.tenant.name})"


class ContactList(models.Model):
    """Segmented contact lists for email campaigns"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='contact_lists')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Filter criteria (stored as JSON for flexibility)
    filter_criteria = models.JSONField(
        default=dict,
        blank=True,
        help_text="Criteria for automatically including contacts (e.g., contact_type, tags, lifecycle_stage)"
    )
    
    # Manual contacts (if not using filters)
    contacts = models.ManyToManyField('api.Contact', blank=True, related_name='contact_lists')
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='created_contact_lists')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.tenant.name})"
    
    def get_contacts(self):
        """Get all contacts in this list based on filter criteria"""
        from api.models.crm import Contact as CRMContact
        
        queryset = CRMContact.objects.filter(tenant=self.tenant)
        
        # Apply filter criteria
        if self.filter_criteria:
            if 'contact_type' in self.filter_criteria:
                queryset = queryset.filter(contact_type=self.filter_criteria['contact_type'])
            if 'lifecycle_stage' in self.filter_criteria:
                queryset = queryset.filter(lifecycle_stage=self.filter_criteria['lifecycle_stage'])
            if 'tags' in self.filter_criteria:
                tag_ids = self.filter_criteria['tags']
                queryset = queryset.filter(tags__id__in=tag_ids)
        
        # Add manually added contacts
        manual_contacts = self.contacts.all()
        queryset = queryset | CRMContact.objects.filter(id__in=[c.id for c in manual_contacts])
        
        return queryset.distinct()
    
    @property
    def contact_count(self):
        return self.get_contacts().count()


class EmailCampaign(models.Model):
    """Email marketing campaigns"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('sending', 'Sending'),
        ('sent', 'Sent'),
        ('paused', 'Paused'),
        ('cancelled', 'Cancelled'),
    ]
    
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='email_campaigns')
    name = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    body_html = models.TextField()
    body_text = models.TextField(blank=True)
    
    # Template (optional - can create from template or from scratch)
    template = models.ForeignKey(EmailTemplate, on_delete=models.SET_NULL, blank=True, null=True, related_name='campaigns')
    
    # Recipients
    contact_list = models.ForeignKey(ContactList, on_delete=models.SET_NULL, blank=True, null=True, related_name='campaigns')
    recipients = models.ManyToManyField('api.Contact', blank=True, related_name='email_campaigns')
    
    # Scheduling
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    scheduled_at = models.DateTimeField(blank=True, null=True)
    sent_at = models.DateTimeField(blank=True, null=True)
    
    # Sender
    from_email = models.EmailField(blank=True, null=True)
    from_name = models.CharField(max_length=255, blank=True, null=True)
    reply_to = models.EmailField(blank=True, null=True)
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='created_email_campaigns')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['tenant', 'scheduled_at']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.tenant.name})"
    
    @property
    def total_recipients(self):
        if self.contact_list:
            return self.contact_list.contact_count
        return self.recipients.count()
    
    @property
    def sent_count(self):
        return self.email_activities.filter(status='sent').count()
    
    @property
    def opened_count(self):
        return self.email_activities.filter(opened_at__isnull=False).count()
    
    @property
    def clicked_count(self):
        return self.email_activities.filter(clicked_at__isnull=False).count()
    
    @property
    def open_rate(self):
        if self.sent_count == 0:
            return 0
        return (self.opened_count / self.sent_count) * 100
    
    @property
    def click_rate(self):
        if self.sent_count == 0:
            return 0
        return (self.clicked_count / self.sent_count) * 100


class EmailActivity(models.Model):
    """Track individual email sends and interactions"""
    campaign = models.ForeignKey(EmailCampaign, on_delete=models.CASCADE, related_name='email_activities')
    contact = models.ForeignKey('api.Contact', on_delete=models.CASCADE, related_name='email_activities')
    
    # Status
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('bounced', 'Bounced'),
        ('failed', 'Failed'),
    ], default='pending')
    
    # Timestamps
    sent_at = models.DateTimeField(blank=True, null=True)
    delivered_at = models.DateTimeField(blank=True, null=True)
    opened_at = models.DateTimeField(blank=True, null=True)
    clicked_at = models.DateTimeField(blank=True, null=True)
    bounced_at = models.DateTimeField(blank=True, null=True)
    
    # Tracking
    open_count = models.IntegerField(default=0)
    click_count = models.IntegerField(default=0)
    bounce_reason = models.TextField(blank=True, null=True)
    
    # Links clicked (stored as JSON array)
    links_clicked = models.JSONField(default=list, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['campaign', 'contact']
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['campaign', 'status']),
            models.Index(fields=['contact', 'status']),
        ]
    
    def __str__(self):
        return f"{self.campaign.name} → {self.contact.full_name}"


class EmailSequence(models.Model):
    """Automated email sequences (drip campaigns)"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='email_sequences')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Trigger
    trigger_event = models.CharField(max_length=50, choices=[
        ('contact_created', 'Contact Created'),
        ('deal_stage_changed', 'Deal Stage Changed'),
        ('activity_completed', 'Activity Completed'),
        ('manual', 'Manual Trigger'),
    ], default='manual')
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='created_email_sequences')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.tenant.name})"


class EmailSequenceStep(models.Model):
    """Steps in an email sequence"""
    sequence = models.ForeignKey(EmailSequence, on_delete=models.CASCADE, related_name='steps')
    order = models.IntegerField(default=0)
    
    # Email details
    template = models.ForeignKey(EmailTemplate, on_delete=models.SET_NULL, blank=True, null=True)
    subject = models.CharField(max_length=255, blank=True)
    body_html = models.TextField(blank=True)
    
    # Timing
    delay_days = models.IntegerField(default=0, help_text="Days to wait before sending this step")
    delay_hours = models.IntegerField(default=0, help_text="Additional hours to wait")
    
    # Conditions (optional - only send if conditions are met)
    conditions = models.JSONField(
        default=dict,
        blank=True,
        help_text="Conditions that must be met to send this step"
    )
    
    class Meta:
        ordering = ['sequence', 'order']
        unique_together = ['sequence', 'order']
    
    def __str__(self):
        return f"{self.sequence.name} - Step {self.order}"

