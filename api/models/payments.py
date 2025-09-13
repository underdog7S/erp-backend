from django.db import models
from django.conf import settings
from api.models.user import UserProfile, Tenant
from api.models.plan import Plan

class PaymentTransaction(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True, blank=True)
    order_id = models.CharField(max_length=100)
    payment_id = models.CharField(max_length=100)
    signature = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='INR')
    status = models.CharField(max_length=30, default='created')  # created, verified, failed
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.tenant} - {self.plan} - {self.amount} {self.currency} ({self.status})" 