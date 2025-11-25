from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from api.models.user import Tenant
import json


class ContactTag(models.Model):
    """Tags for categorizing contacts"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='contact_tags')
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=7, default='#1976d2')  # Hex color code
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['tenant', 'name']
        ordering = ['name']
    
    def __str__(self):
        return f"{self.tenant.name} - {self.name}"


class Contact(models.Model):
    """Unified contact model for all tenant types"""
    CONTACT_TYPES = [
        ('student', 'Student'),
        ('parent', 'Parent'),
        ('guest', 'Guest'),
        ('customer', 'Customer'),
        ('patient', 'Patient'),
        ('client', 'Client'),
        ('lead', 'Lead'),
        ('vendor', 'Vendor'),
        ('other', 'Other'),
    ]
    
    LIFECYCLE_STAGES = [
        ('lead', 'Lead'),
        ('customer', 'Customer'),
        ('opportunity', 'Opportunity'),
        ('vip', 'VIP'),
        ('inactive', 'Inactive'),
    ]
    
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='contacts')
    contact_type = models.CharField(max_length=20, choices=CONTACT_TYPES, default='customer')
    lifecycle_stage = models.CharField(max_length=20, choices=LIFECYCLE_STAGES, default='lead')
    
    # Basic Information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    mobile = models.CharField(max_length=20, blank=True, null=True)
    
    # Address
    address_line1 = models.CharField(max_length=255, blank=True, null=True)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    
    # Additional Information
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=20, blank=True, null=True)
    job_title = models.CharField(max_length=100, blank=True, null=True)
    company = models.ForeignKey('Company', on_delete=models.SET_NULL, blank=True, null=True, related_name='contacts')
    
    # Communication Preferences
    email_opt_in = models.BooleanField(default=True)
    sms_opt_in = models.BooleanField(default=False)
    preferred_contact_method = models.CharField(max_length=20, choices=[
        ('email', 'Email'),
        ('phone', 'Phone'),
        ('sms', 'SMS'),
        ('whatsapp', 'WhatsApp'),
    ], default='email')
    
    # Tags and Custom Fields
    tags = models.ManyToManyField(ContactTag, blank=True, related_name='contacts')
    custom_fields = models.JSONField(default=dict, blank=True)  # Flexible custom fields
    
    # Metadata
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='owned_contacts')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='created_contacts')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_contacted_at = models.DateTimeField(blank=True, null=True)
    
    # Notes
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'email']),
            models.Index(fields=['tenant', 'phone']),
            models.Index(fields=['tenant', 'contact_type']),
            models.Index(fields=['tenant', 'lifecycle_stage']),
        ]
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.tenant.name})"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def full_address(self):
        parts = [self.address_line1, self.address_line2, self.city, self.state, self.postal_code, self.country]
        return ', '.join([p for p in parts if p])


class Company(models.Model):
    """Company/Organization model for B2B relationships"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='companies')
    name = models.CharField(max_length=255)
    industry = models.CharField(max_length=100, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    
    # Address
    address_line1 = models.CharField(max_length=255, blank=True, null=True)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    
    # Company Details
    company_size = models.CharField(max_length=50, blank=True, null=True)  # e.g., "1-10", "11-50", "51-200"
    annual_revenue = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    
    # Hierarchy
    parent_company = models.ForeignKey('self', on_delete=models.SET_NULL, blank=True, null=True, related_name='subsidiaries')
    
    # Tags and Custom Fields
    tags = models.ManyToManyField(ContactTag, blank=True, related_name='companies')
    custom_fields = models.JSONField(default=dict, blank=True)
    
    # Metadata
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='owned_companies')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='created_companies')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_contacted_at = models.DateTimeField(blank=True, null=True)
    
    # Notes
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name_plural = 'Companies'
        ordering = ['name']
        indexes = [
            models.Index(fields=['tenant', 'name']),
            models.Index(fields=['tenant', 'industry']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.tenant.name})"
    
    @property
    def contact_count(self):
        return self.contacts.count()
    
    @property
    def full_address(self):
        parts = [self.address_line1, self.address_line2, self.city, self.state, self.postal_code, self.country]
        return ', '.join([p for p in parts if p])


class Activity(models.Model):
    """Unified activity model for calls, emails, meetings, tasks, notes"""
    ACTIVITY_TYPES = [
        ('call', 'Call'),
        ('email', 'Email'),
        ('meeting', 'Meeting'),
        ('task', 'Task'),
        ('note', 'Note'),
        ('sms', 'SMS'),
        ('whatsapp', 'WhatsApp'),
    ]
    
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    
    # Relationships
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='activities', blank=True, null=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='activities', blank=True, null=True)
    
    # Activity Details
    subject = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    
    # Timing
    activity_date = models.DateTimeField(default=timezone.now)
    duration_minutes = models.IntegerField(blank=True, null=True)  # For calls/meetings
    
    # Status
    status = models.CharField(max_length=20, choices=[
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ], default='scheduled')
    
    # Outcome
    outcome = models.CharField(max_length=100, blank=True, null=True)  # e.g., "Interested", "Not Interested", "Follow-up Needed"
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='created_activities')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='assigned_activities')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Attachments (stored as JSON array of file paths/URLs)
    attachments = models.JSONField(default=list, blank=True)
    
    class Meta:
        verbose_name_plural = 'Activities'
        ordering = ['-activity_date']
        indexes = [
            models.Index(fields=['tenant', 'activity_type']),
            models.Index(fields=['tenant', 'activity_date']),
            models.Index(fields=['contact', 'activity_date']),
        ]
    
    def __str__(self):
        return f"{self.get_activity_type_display()} - {self.subject}"


class Deal(models.Model):
    """Deal/Opportunity model for sales pipeline"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='deals')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    
    # Financial
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    
    # Relationships
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='deals', blank=True, null=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='deals', blank=True, null=True)
    
    # Pipeline
    stage = models.CharField(max_length=50, default='lead')  # Will be managed via DealStage model
    probability = models.IntegerField(default=0, help_text="Probability of closing (0-100%)")
    
    # Dates
    close_date = models.DateField(blank=True, null=True)
    expected_close_date = models.DateField(blank=True, null=True)
    
    # Status
    won = models.BooleanField(default=False)
    lost = models.BooleanField(default=False)
    lost_reason = models.TextField(blank=True, null=True)
    
    # Metadata
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='owned_deals')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='created_deals')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Custom Fields
    custom_fields = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'stage']),
            models.Index(fields=['tenant', 'close_date']),
            models.Index(fields=['contact', 'stage']),
        ]
    
    def __str__(self):
        return f"{self.name} - ₹{self.amount} ({self.tenant.name})"
    
    @property
    def weighted_amount(self):
        """Calculate weighted deal value (amount * probability)"""
        return float(self.amount) * (self.probability / 100)


class DealStage(models.Model):
    """Customizable deal stages for pipeline"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='deal_stages')
    name = models.CharField(max_length=100)
    order = models.IntegerField(default=0)
    probability = models.IntegerField(default=0, help_text="Default probability for this stage (0-100%)")
    is_closed = models.BooleanField(default=False, help_text="Is this a closed stage?")
    color = models.CharField(max_length=7, default='#1976d2')
    
    class Meta:
        unique_together = ['tenant', 'name']
        ordering = ['order']
    
    def __str__(self):
        return f"{self.tenant.name} - {self.name}"

