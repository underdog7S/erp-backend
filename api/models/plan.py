from django.db import models

class Plan(models.Model):
    BILLING_CYCLES = [
        ('monthly', 'Monthly'),
        ('annual', 'Annual'),
        ('custom', 'Custom'),
    ]
    
    name = models.CharField(max_length=100)
    description = models.TextField()
    max_users = models.IntegerField(null=True, blank=True)  # null for unlimited
    storage_limit_mb = models.IntegerField()
    price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)  # null for custom pricing
    billing_cycle = models.CharField(max_length=20, choices=BILLING_CYCLES, default='monthly')
    monthly_equivalent = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    color = models.CharField(max_length=7, default='#2196F3')  # hex color
    popular = models.BooleanField(default=False)
    savings_text = models.CharField(max_length=100, blank=True)
    
    # Feature flags
    has_inventory = models.BooleanField(default=False)
    has_education = models.BooleanField(default=False)
    has_pharmacy = models.BooleanField(default=False)
    has_retail = models.BooleanField(default=False)
    has_hotel = models.BooleanField(default=False)
    has_restaurant = models.BooleanField(default=False)
    has_salon = models.BooleanField(default=False)
    has_healthcare = models.BooleanField(default=False)
    has_dashboard = models.BooleanField(default=True)
    has_analytics = models.BooleanField(default=False)
    has_qc = models.BooleanField(default=False)
    has_billing = models.BooleanField(default=False)
    has_api_access = models.BooleanField(default=False)
    has_audit_logs = models.BooleanField(default=False)
    has_priority_support = models.BooleanField(default=False)
    has_phone_support = models.BooleanField(default=False)
    has_white_label = models.BooleanField(default=False)
    has_onboarding = models.BooleanField(default=False)
    has_sla_support = models.BooleanField(default=False)
    has_daily_backups = models.BooleanField(default=False)
    has_strategy_call = models.BooleanField(default=False)
    has_custom_reports = models.BooleanField(default=False)
    has_future_discount = models.BooleanField(default=False)
    has_new_features_access = models.BooleanField(default=False)

    class Meta:
        app_label = 'api'

    def __str__(self):
        return self.name

    def has_feature(self, feature_name):
        return getattr(self, f"has_{feature_name}", False)
    
    @property
    def is_unlimited_users(self):
        return self.max_users is None
    
    @property
    def is_custom_pricing(self):
        return self.price is None
    
    @property
    def display_price(self):
        if self.is_custom_pricing:
            return "Custom"
        if self.price == 0:
            return "Free"
        return f"₹{self.price}"
    
    @property
    def display_users(self):
        if self.is_unlimited_users:
            return "Unlimited"
        return str(self.max_users)
