from django.db import models
from django.utils import timezone


class VisitorLead(models.Model):
    """
    Capture anonymous visitor metadata from zenitherp.online before they become authenticated customers.
    """
    visitor_token = models.CharField(max_length=64, unique=True, help_text="Cookie/UUID tied to this visitor")
    ip_address = models.CharField(max_length=45, blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    landing_url = models.URLField(max_length=1024, blank=True, null=True)
    referrer = models.URLField(max_length=1024, blank=True, null=True)
    utm_source = models.CharField(max_length=128, blank=True, null=True)
    utm_medium = models.CharField(max_length=128, blank=True, null=True)
    utm_campaign = models.CharField(max_length=128, blank=True, null=True)
    utm_term = models.CharField(max_length=128, blank=True, null=True)
    utm_content = models.CharField(max_length=128, blank=True, null=True)
    form_submitted = models.BooleanField(default=False, help_text="True once the visitor sends any form data")
    submitted_name = models.CharField(max_length=255, blank=True, null=True)
    submitted_email = models.EmailField(blank=True, null=True)
    submitted_phone = models.CharField(max_length=30, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    last_seen = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Visitor Lead"
        verbose_name_plural = "Visitor Leads"

    def mark_form_submitted(self, **kwargs):
        self.form_submitted = True
        for key, value in kwargs.items():
            if hasattr(self, key) and value:
                setattr(self, key, value)
        self.last_seen = timezone.now()
        self.save()

    def __str__(self):
        return f"Visitor {self.visitor_token[:8]} ({self.ip_address or 'unknown IP'})"

