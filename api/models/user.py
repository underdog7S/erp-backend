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
    name = models.CharField(max_length=100)
    industry = models.CharField(max_length=50, choices=INDUSTRY_CHOICES)
    # Link to Plan model for plan-based controls
    plan = models.ForeignKey('api.Plan', on_delete=models.SET_NULL, null=True, blank=True)
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
    created_at = models.DateTimeField(auto_now_add=True)
    
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
