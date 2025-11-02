from django.contrib import admin
from api.models.user import UserProfile, Role
from api.models.audit import AuditLog
from api.models.custom_service import CustomServiceRequest
from .models.payments import PaymentTransaction
from education.models import Class
from api.admin_site import secure_admin_site

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'tenant', 'role', 'department', 'get_assigned_classes')
    search_fields = ('user__username', 'user__email', 'role__name', 'department__name')
    list_filter = ('tenant', 'role', 'department')
    filter_horizontal = ('assigned_classes',)
    fieldsets = (
        (None, {'fields': ('user', 'tenant', 'role', 'department', 'assigned_classes')}),
        ('Personal Info', {'fields': ('photo', 'phone', 'address', 'date_of_birth', 'gender', 'emergency_contact', 'job_title', 'joining_date', 'qualifications', 'bio', 'linkedin')}),
    )
    
    def get_assigned_classes(self, obj):
        """Display assigned classes in list view"""
        classes = obj.assigned_classes.all()
        return ', '.join([cls.name for cls in classes]) if classes else '-'
    get_assigned_classes.short_description = 'Assigned Classes'
    
    def get_form(self, request, obj=None, **kwargs):
        """Filter assigned_classes queryset by tenant"""
        form = super().get_form(request, obj, **kwargs)
        
        # Get the tenant from the object or from the request
        if obj and obj.tenant:
            tenant = obj.tenant
        elif 'tenant' in request.GET:
            # Try to get tenant from request if available
            from api.models.user import Tenant
            try:
                tenant = Tenant.objects.get(id=request.GET['tenant'])
            except:
                tenant = None
        else:
            tenant = None
        
        # Filter classes by tenant
        if tenant:
            form.base_fields['assigned_classes'].queryset = Class.objects.filter(tenant=tenant)
        else:
            form.base_fields['assigned_classes'].queryset = Class.objects.all()
        
        return form
    
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """Filter assigned_classes by tenant when adding/editing"""
        if db_field.name == 'assigned_classes':
            # Get tenant from the object being edited or from request
            obj = kwargs.get('obj')
            if obj and obj.tenant:
                kwargs['queryset'] = Class.objects.filter(tenant=obj.tenant)
            else:
                kwargs['queryset'] = Class.objects.all()
        return super().formfield_for_manytomany(db_field, request, **kwargs)

# Register with secure admin site instead of default admin
secure_admin_site.register(UserProfile, UserProfileAdmin)

class AuditLogAdmin(admin.ModelAdmin):
    """Admin interface for audit logs - read-only for security"""
    list_display = ('id', 'user', 'action', 'resource_type', 'resource_name', 'ip_address', 'success', 'created_at')
    list_filter = ('action', 'resource_type', 'success', 'created_at')
    search_fields = ('user__username', 'user__email', 'resource_type', 'resource_name', 'ip_address', 'description')
    readonly_fields = ('user', 'user_profile', 'action', 'resource_type', 'resource_id', 'resource_name', 
                       'ip_address', 'user_agent', 'request_method', 'request_path', 'request_data', 
                       'response_status', 'description', 'success', 'error_message', 'created_at')
    date_hierarchy = 'created_at'
    
    def has_add_permission(self, request):
        """Prevent manual creation of audit logs"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent modification of audit logs"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Only allow deletion by superusers"""
        return request.user.is_superuser

secure_admin_site.register(AuditLog, AuditLogAdmin)

class PaymentTransactionAdmin(admin.ModelAdmin):
    """Admin interface for payment transactions"""
    list_display = ('id', 'user', 'tenant', 'plan', 'amount', 'currency', 'status', 'order_id', 'payment_id', 'created_at', 'verified_at')
    list_filter = ('status', 'currency', 'created_at', 'verified_at', 'tenant', 'plan')
    search_fields = ('user__username', 'user__email', 'order_id', 'payment_id', 'tenant__name')
    readonly_fields = ('order_id', 'payment_id', 'signature', 'created_at', 'verified_at')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)

secure_admin_site.register(PaymentTransaction, PaymentTransactionAdmin)

class CustomServiceRequestAdmin(admin.ModelAdmin):
    """Admin interface for custom service requests"""
    list_display = ('id', 'name', 'email', 'phone', 'service_type', 'company_name', 'status', 'submitted_at')
    list_filter = ('service_type', 'status', 'submitted_at')
    search_fields = ('name', 'email', 'phone', 'company_name', 'description')
    readonly_fields = ('submitted_at',)
    fieldsets = (
        ('Contact Information', {
            'fields': ('name', 'email', 'phone', 'company_name')
        }),
        ('Service Details', {
            'fields': ('service_type', 'description', 'budget_range', 'timeline')
        }),
        ('Status & Notes', {
            'fields': ('status', 'notes', 'submitted_at', 'contacted_at')
        }),
    )
    date_hierarchy = 'submitted_at'
    ordering = ('-submitted_at',)

secure_admin_site.register(CustomServiceRequest, CustomServiceRequestAdmin)