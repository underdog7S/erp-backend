from django.db import models
from .user import Tenant
from .crm import Contact
from django.contrib.auth.models import User

class CommunicationThread(models.Model):
    SOURCE_CHOICES = [
        ('whatsapp', 'WhatsApp'),
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('system', 'System')
    ]
    
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='communication_threads')
    contact = models.ForeignKey(Contact, on_delete=models.SET_NULL, null=True, blank=True, related_name='communication_threads')
    
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    
    # External IDs for routing
    external_thread_id = models.CharField(max_length=255, blank=True, null=True, help_text="E.g., WhatsApp Phone Number or Email Subject Hash")
    
    # Metadata
    subject = models.CharField(max_length=255, blank=True, null=True)
    is_closed = models.BooleanField(default=False)
    has_unread = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.source.upper()} Thread - {self.contact.full_name if self.contact else 'Unknown'}"

    class Meta:
        ordering = ['-updated_at']

class CommunicationMessage(models.Model):
    SENDER_TYPE_CHOICES = [
        ('client', 'Client'),
        ('agent', 'Agent'),
        ('ai', 'AI Bot')
    ]
    
    thread = models.ForeignKey(CommunicationThread, on_delete=models.CASCADE, related_name='messages')
    
    sender_type = models.CharField(max_length=20, choices=SENDER_TYPE_CHOICES)
    agent = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, help_text="If agent sent this")
    
    content = models.TextField()
    
    # Message metadata
    external_message_id = models.CharField(max_length=255, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender_type} - {self.content[:30]}"
        
    class Meta:
        ordering = ['created_at']
