from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import uuid

class EmailVerification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Verification for {self.email}"
    
    @property
    def is_expired(self):
        # Token expires after 24 hours
        return timezone.now() > (self.created_at + timedelta(hours=24))
    
    def verify(self):
        self.is_verified = True
        self.verified_at = timezone.now()
        self.save()
        
        # Also verify the user's email
        user = self.user
        user.is_active = True
        user.save() 