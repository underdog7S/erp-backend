from django.db import models

class Plan(models.Model):
    BILLING_CYCLES = [
        ('monthly', 'Monthly'),
        ('annual', 'Annual'),
        ('custom', 'Custom'),
    ]
    
    name = models.CharField(
        max_length=100,
        help_text="Plan display name (e.g., 'Free', 'Starter', 'Pro', 'Business'). This appears on pricing pages."
    )
    description = models.TextField(
        help_text="Short description shown on pricing page (e.g., 'Perfect for getting started', 'Ideal for growing businesses')"
    )
    max_users = models.IntegerField(
        null=True, 
        blank=True,
        help_text="Maximum number of users allowed. Leave BLANK for unlimited users. Examples: Free=2, Starter=25, Pro=100"
    )
    storage_limit_mb = models.IntegerField(
        help_text="Storage limit in Megabytes. 1 GB = 1024 MB. Examples: 500 MB = 500, 5 GB = 5120, 20 GB = 20480, 50 GB = 51200"
    )
    price = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Price in Indian Rupees (₹). Set to 0 for Free plan. Leave blank for Custom/Enterprise pricing."
    )
    billing_cycle = models.CharField(
        max_length=20, 
        choices=BILLING_CYCLES, 
        default='monthly',
        help_text="Billing frequency: Monthly (Free), Annual (paid plans), or Custom (Enterprise)"
    )
    monthly_equivalent = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Monthly equivalent price for annual plans. Example: ₹4,500/year = ₹375/month (for display purposes)"
    )
    color = models.CharField(
        max_length=7, 
        default='#2196F3',
        help_text="Hex color code for plan badge/UI (e.g., #2196F3=blue, #4CAF50=green, #FF9800=orange, #9C27B0=purple)"
    )
    popular = models.BooleanField(
        default=False,
        help_text="Mark as 'Most Popular' to highlight on homepage with badge and special styling"
    )
    savings_text = models.CharField(
        max_length=100, 
        blank=True,
        help_text="Optional savings message (e.g., 'Save ₹2,989 annually') shown on pricing page"
    )
    
    # Feature flags - Industry Modules
    has_inventory = models.BooleanField(
        default=False,
        help_text="Base inventory management (usually enabled by industry modules)"
    )
    has_education = models.BooleanField(
        default=False,
        help_text="Education ERP: Students, Classes, Fees, Attendance, Report Cards"
    )
    has_pharmacy = models.BooleanField(
        default=False,
        help_text="Pharmacy Management: Medicines, Prescriptions, Sales, Inventory"
    )
    has_retail = models.BooleanField(
        default=False,
        help_text="Retail/Wholesale: Products, Warehouses, Multi-location inventory, Sales"
    )
    has_hotel = models.BooleanField(
        default=False,
        help_text="Hotel Management: Rooms, Bookings, Guests, Check-in/out"
    )
    has_restaurant = models.BooleanField(
        default=False,
        help_text="Restaurant Management: Menu, Tables, Orders, Kitchen display"
    )
    has_salon = models.BooleanField(
        default=False,
        help_text="Salon Management: Services, Appointments, Stylists, Customers"
    )
    has_healthcare = models.BooleanField(
        default=False,
        help_text="Healthcare Management: Patients, Appointments, Medical records (Future feature)"
    )
    
    # Feature flags - Core Features
    has_dashboard = models.BooleanField(
        default=True,
        help_text="Main dashboard access - Shows overview, stats, quick actions (usually ON for all plans)"
    )
    has_analytics = models.BooleanField(
        default=False,
        help_text="Advanced analytics and reporting: Charts, trends, forecasting, custom reports"
    )
    has_qc = models.BooleanField(
        default=False,
        help_text="Quality Control: QC workflows, approval processes, quality checks"
    )
    has_billing = models.BooleanField(
        default=False,
        help_text="Billing Management: Invoice generation, payment tracking, billing features"
    )
    has_api_access = models.BooleanField(
        default=False,
        help_text="REST API access for integrations: Connect external systems, mobile apps, third-party tools"
    )
    has_audit_logs = models.BooleanField(
        default=False,
        help_text="Audit Logging: Track all user actions, who did what, when, from where (for security/compliance)"
    )
    has_priority_support = models.BooleanField(
        default=False,
        help_text="Priority Support: Faster response times, priority queue for support tickets"
    )
    has_phone_support = models.BooleanField(
        default=False,
        help_text="Phone Support: Direct phone number, call scheduling, voice support availability"
    )
    has_white_label = models.BooleanField(
        default=False,
        help_text="White Label: Remove Zenith ERP branding, allow custom logo, colors, branding"
    )
    has_onboarding = models.BooleanField(
        default=False,
        help_text="Onboarding Assistance: Dedicated setup help, training, migration support"
    )
    has_sla_support = models.BooleanField(
        default=False,
        help_text="SLA Support: Service Level Agreement guarantee, uptime commitment, response time guarantees"
    )
    has_daily_backups = models.BooleanField(
        default=False,
        help_text="Daily Backups: Automated daily data backups, point-in-time recovery"
    )
    has_strategy_call = models.BooleanField(
        default=False,
        help_text="Strategy Call: 1-on-1 consultation call with expert, business analysis, optimization advice"
    )
    has_custom_reports = models.BooleanField(
        default=False,
        help_text="Custom Reports: Create custom report templates, layouts, schedules with custom fields"
    )
    has_future_discount = models.BooleanField(
        default=False,
        help_text="Future Discount: Discount on future upgrades/add-ons (typically 10-20% off)"
    )
    has_new_features_access = models.BooleanField(
        default=False,
        help_text="New Features Access: Early access to new features (beta), test before general release"
    )

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
