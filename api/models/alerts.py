from django.db import models
from api.models.user import Tenant

class Alert(models.Model):
    ALERT_TYPES = [
        ("usage", "Usage Limit"),
        ("plan", "Plan Expiry"),
        ("general", "General")
    ]
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    message = models.TextField()
    type = models.CharField(max_length=20, choices=ALERT_TYPES, default="general")
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)
    def __str__(self):
        return f"{self.tenant.name}: {self.type} - {self.message[:30]}" 