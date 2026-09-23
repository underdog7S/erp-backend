from django.db import models
from django.contrib.auth.models import User
from .user import Tenant

class ChatChannel(models.Model):
    CHANNEL_TYPE_CHOICES = [
        ('direct', 'Direct Message'),
        ('group', 'Group'),
        ('ai', 'AI Assistant'),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='chat_channels')
    name = models.CharField(max_length=100, blank=True, help_text="Blank for direct messages, shown for groups")
    channel_type = models.CharField(max_length=10, choices=CHANNEL_TYPE_CHOICES)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='chat_channels_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name or f"DM #{self.id}"

    class Meta:
        ordering = ['-updated_at']

class ChatChannelMembership(models.Model):
    channel = models.ForeignKey(ChatChannel, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_memberships')
    last_read_at = models.DateTimeField(null=True, blank=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('channel', 'user')

class ChatMessage(models.Model):
    channel = models.ForeignKey(ChatChannel, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='chat_messages_sent')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender_id} - {self.content[:30]}"

    class Meta:
        ordering = ['created_at']
