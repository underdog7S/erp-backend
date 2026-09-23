import secrets
from django.db import models
from .user import Tenant


def _new_public_key():
    return secrets.token_urlsafe(12)


class LeadCaptureConfig(models.Model):
    """Per-tenant settings for the public enquiry form/widget and the
    service area used to flag leads as inside/outside the area."""
    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE, related_name='lead_capture_config')
    public_key = models.CharField(max_length=32, unique=True, default=_new_public_key)
    is_active = models.BooleanField(default=True)
    business_name = models.CharField(max_length=150, blank=True)
    intro_message = models.CharField(max_length=300, blank=True, default='Tell us what you need and we will get back to you.')
    success_message = models.CharField(max_length=300, blank=True, default='Thank you! We have received your enquiry and will contact you soon.')
    center_query = models.CharField(max_length=200, blank=True, help_text="Pincode or address of the service-area center")
    center_lat = models.FloatField(null=True, blank=True)
    center_lng = models.FloatField(null=True, blank=True)
    service_radius_km = models.PositiveIntegerField(null=True, blank=True, help_text="Blank = serve anywhere")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Lead capture for {self.tenant.name}"


class GeocodeCache(models.Model):
    """Caches Nominatim lookups (including misses) so the free public service
    is queried at most once per place, per its usage policy."""
    query = models.CharField(max_length=200, unique=True)
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
