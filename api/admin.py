from django.contrib import admin
from api.models.user import UserProfile, Role
from api.models.audit import AuditLog
from .models.payments import PaymentTransaction
from education.models import Class

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

admin.site.register(UserProfile, UserProfileAdmin)

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

admin.site.register(AuditLog, AuditLogAdmin)