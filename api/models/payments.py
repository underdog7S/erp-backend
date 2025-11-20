from django.db import models
from django.conf import settings
from api.models.user import UserProfile, Tenant
from api.models.plan import Plan

class PaymentTransaction(models.Model):
    """Payment transactions from Razorpay - tracks all sector payments"""
    SECTOR_CHOICES = [
        ('plan', 'Plan Subscription'),
        ('education', 'Education Fee'),
        ('restaurant', 'Restaurant Order'),
        ('salon', 'Salon Appointment'),
        ('pharmacy', 'Pharmacy Sale'),
        ('retail', 'Retail Sale'),
        ('hotel', 'Hotel Booking'),
        ('general', 'General Payment'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, 
                             help_text="User who initiated payment (null for webhook payments)")
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True, blank=True)
    order_id = models.CharField(max_length=100, db_index=True)
    payment_id = models.CharField(max_length=100, unique=True, db_index=True)  # Razorpay payment_id is unique globally
    signature = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='INR')
    status = models.CharField(max_length=30, default='created')  # created, verified, failed
    # Sector and reference tracking
    sector = models.CharField(max_length=20, choices=SECTOR_CHOICES, default='general', db_index=True)
    reference_id = models.CharField(max_length=100, null=True, blank=True, db_index=True, 
                                    help_text="ID of the related record (fee_payment_id, order_id, appointment_id, etc.)")
    description = models.CharField(max_length=255, blank=True, help_text="Human-readable description")
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'sector', 'status']),
            models.Index(fields=['tenant', 'reference_id']),
            models.Index(fields=['payment_id']),
        ]
        # Prevent duplicate payments - same payment_id can only exist once
        constraints = [
            models.UniqueConstraint(fields=['payment_id'], name='unique_payment_id'),
        ]

    def __str__(self):
        sector_display = dict(self.SECTOR_CHOICES).get(self.sector, self.sector)
        return f"{self.tenant} - {sector_display} - ₹{self.amount} ({self.status})"
    
    @property
    def sector_display(self):
        """Get human-readable sector name"""
        return dict(self.SECTOR_CHOICES).get(self.sector, self.sector) 