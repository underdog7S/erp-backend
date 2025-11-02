from django.db import models
from django.utils import timezone

SERVICE_TYPE_CHOICES = [
    ('customization', 'Customization'),
    ('web_development', 'Web Development'),
    ('app_development', 'App Development'),
    ('both', 'Web + App Development'),
]

STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('contacted', 'Contacted'),
    ('in_progress', 'In Progress'),
    ('completed', 'Completed'),
    ('cancelled', 'Cancelled'),
]

class CustomServiceRequest(models.Model):
    """Model to store custom service requests from homepage"""
    service_type = models.CharField(
        max_length=50,
        choices=SERVICE_TYPE_CHOICES,
        help_text="Type of service requested"
    )
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    company_name = models.CharField(max_length=200, blank=True)
    description = models.TextField(help_text="Detailed description of requirements")
    budget_range = models.CharField(
        max_length=50,
        blank=True,
        help_text="Budget range (e.g., '10k-50k', '50k-1L', '1L+')"
    )
    timeline = models.CharField(
        max_length=100,
        blank=True,
        help_text="Expected timeline (e.g., '1 month', '3 months', '6 months')"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    notes = models.TextField(blank=True, help_text="Internal notes for admin")
    submitted_at = models.DateTimeField(default=timezone.now)
    contacted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-submitted_at']
        verbose_name = 'Custom Service Request'
        verbose_name_plural = 'Custom Service Requests'
    
    def __str__(self):
        return f"{self.name} - {self.get_service_type_display()} ({self.status})"

