from django.db import models
from django.contrib.auth.models import User
# from api.models.education import Class  # Remove this import to avoid circular import

INDUSTRY_CHOICES = [
    ("manufacturing", "Manufacturing"),
    ("education", "Education"),
    ("healthcare", "Healthcare"),
    ("pharmacy", "Pharmacy"),
    ("retail", "Retail"),
    ("hotel", "Hotel"),
    ("restaurant", "Restaurant"),
    ("salon", "Salon"),
]

class Role(models.Model):
    """Defines user roles within a tenant (e.g., admin, staff, teacher, accountant, librarian, principal, student, etc.)."""
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    def __str__(self):
        return self.name

class Tenant(models.Model):
    SUBSCRIPTION_STATUS_CHOICES = [
        ('active', 'Active'),
        ('expiring_soon', 'Expiring Soon'),
        ('expired', 'Expired'),
        ('suspended', 'Suspended'),
        ('grace_period', 'Grace Period'),
    ]
    
    name = models.CharField(max_length=100)
    industry = models.CharField(max_length=50, choices=INDUSTRY_CHOICES)
    # Link to Plan model for plan-based controls
    plan = models.ForeignKey('api.Plan', on_delete=models.SET_NULL, null=True, blank=True)
    # Subscription management
    subscription_start_date = models.DateField(null=True, blank=True, help_text="Date when current subscription started")
    subscription_end_date = models.DateField(null=True, blank=True, help_text="Date when current subscription expires")
    subscription_status = models.CharField(
        max_length=20,
        choices=SUBSCRIPTION_STATUS_CHOICES,
        default='active',
        help_text="Current subscription status"
    )
    grace_period_end_date = models.DateField(null=True, blank=True, help_text="End date of grace period after expiration")
    # Public integrations
    slug = models.SlugField(max_length=50, unique=True, null=True, blank=True)
    public_booking_enabled = models.BooleanField(default=False)
    public_orders_enabled = models.BooleanField(default=False)
    public_admissions_enabled = models.BooleanField(default=False)
    public_api_key = models.CharField(max_length=80, null=True, blank=True)
    # Tenant-level module toggles (some tenants can enable multiple modules)
    has_hotel = models.BooleanField(default=False)
    has_restaurant = models.BooleanField(default=False)
    has_salon = models.BooleanField(default=False)
    storage_used_mb = models.FloatField(default=0)
    logo = models.ImageField(upload_to='tenant_logos/', null=True, blank=True, help_text="Organization logo for reports, bills, and documents")
    # Education module: Percentage calculation settings
    PERCENTAGE_CALCULATION_CHOICES = [
        ('SIMPLE', 'Simple: (Total Marks / Max Marks) × 100'),
        ('SUBJECT_WISE', 'Subject-wise: Average of subject percentages'),
        ('WEIGHTED', 'Weighted: Based on subject weightage (if configured)'),
    ]
    percentage_calculation_method = models.CharField(
        max_length=20,
        choices=PERCENTAGE_CALCULATION_CHOICES,
        default='SIMPLE',
        help_text="Method for calculating overall percentage in report cards"
    )
    percentage_excluded_subjects = models.JSONField(
        default=list,
        blank=True,
        help_text="List of subject IDs to exclude from percentage calculation (JSON array)"
    )
    percentage_rounding = models.IntegerField(
        default=2,
        choices=[(0, '0 decimal places'), (1, '1 decimal place'), (2, '2 decimal places')],
        help_text="Number of decimal places for percentage display"
    )
    percentage_calculation_scope = models.CharField(
        max_length=20,
        choices=[
            ('TERM_WISE', 'Term-wise: Calculate percentage for each term separately'),
            ('ALL_TERMS', 'All Terms: Calculate percentage across all terms combined'),
        ],
        default='TERM_WISE',
        help_text="Whether to calculate percentage per term or across all terms"
    )
    # Razorpay Payment Gateway Configuration
    razorpay_key_id = models.CharField(max_length=255, blank=True, null=True, help_text="Razorpay Key ID from dashboard")
    razorpay_key_secret = models.CharField(max_length=255, blank=True, null=True, help_text="Razorpay Key Secret from dashboard")
    razorpay_webhook_secret = models.CharField(max_length=255, blank=True, null=True, help_text="Razorpay Webhook Secret for payment verification")
    razorpay_enabled = models.BooleanField(default=False, help_text="Enable Razorpay payments for this tenant")
    razorpay_setup_completed = models.BooleanField(default=False, help_text="Razorpay setup wizard completed")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def has_razorpay_configured(self):
        """Check if Razorpay is fully configured"""
        return bool(self.razorpay_key_id and self.razorpay_key_secret and self.razorpay_enabled)
    
    def is_subscription_active(self):
        """Check if subscription is currently active"""
        from django.utils import timezone
        if not self.subscription_end_date:
            return True  # No expiration date means always active
        today = timezone.now().date()
        return self.subscription_end_date >= today and self.subscription_status in ['active', 'expiring_soon']
    
    def is_subscription_expired(self):
        """Check if subscription has expired"""
        from django.utils import timezone
        if not self.subscription_end_date:
            return False
        today = timezone.now().date()
        return self.subscription_end_date < today
    
    def days_until_expiry(self):
        """Calculate days until subscription expires"""
        from django.utils import timezone
        if not self.subscription_end_date:
            return None
        today = timezone.now().date()
        delta = self.subscription_end_date - today
        return delta.days
    
    def is_in_grace_period(self):
        """Check if tenant is in grace period"""
        from django.utils import timezone
        if not self.grace_period_end_date:
            return False
        today = timezone.now().date()
        return self.subscription_status == 'grace_period' and self.grace_period_end_date >= today
    
    def has_module(self, module_name: str) -> bool:
        """Return True if this tenant has access to a given module.
        Access requires the plan to include the module (if plan exists)
        and the tenant toggle to be enabled.
        """
        # Check plan feature first (if plan exists)
        if self.plan and hasattr(self.plan, f"has_{module_name}"):
            if not getattr(self.plan, f"has_{module_name}"):
                return False
        # Then check tenant toggle
        return getattr(self, f"has_{module_name}", False)
    def __str__(self):
        return self.name

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
    assigned_classes = models.ManyToManyField('education.Class', blank=True, related_name='staff_members')
    department = models.ForeignKey('education.Department', on_delete=models.SET_NULL, null=True, blank=True)
    # Enhanced fields
    photo = models.ImageField(upload_to='user_photos/', null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, null=True, blank=True)
    emergency_contact = models.CharField(max_length=100, null=True, blank=True)
    job_title = models.CharField(max_length=100, null=True, blank=True)
    joining_date = models.DateField(null=True, blank=True)
    qualifications = models.TextField(null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    linkedin = models.URLField(null=True, blank=True)

    class Meta:
        ordering = ['id']
    def __str__(self):
        from django.contrib.auth.models import User
        username = self.user.username if self.user and isinstance(self.user, User) else "UnknownUser"
        role = self.role.name if self.role else "NoRole"
        tenant = self.tenant.name if self.tenant else "NoTenant"
        return f"{username} ({role}) in {tenant}"
