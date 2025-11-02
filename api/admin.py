from django.contrib import admin
from api.models.user import UserProfile, Role
from api.models.audit import AuditLog
from api.models.custom_service import CustomServiceRequest
from .models.payments import PaymentTransaction
from .models.invoice import Invoice, InvoiceItem, InvoicePayment
from .models.notifications import Notification, NotificationPreference, NotificationTemplate, NotificationLog
from .models.plan import Plan
from .models.support import TicketSLA
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

# Invoice Admin
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'tenant', 'customer_name', 'total_amount', 'status', 'due_date', 'created_at')
    list_filter = ('status', 'tenant', 'created_at', 'due_date')
    search_fields = ('invoice_number', 'customer_name', 'customer_email')
    readonly_fields = ('invoice_number', 'created_at', 'updated_at', 'paid_at')
    date_hierarchy = 'created_at'

secure_admin_site.register(Invoice, InvoiceAdmin)

class InvoiceItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'invoice', 'description', 'quantity', 'unit_price', 'total')
    list_filter = ('invoice__status', 'invoice__tenant')
    search_fields = ('description', 'invoice__invoice_number')

secure_admin_site.register(InvoiceItem, InvoiceItemAdmin)

# Notification Admin
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'tenant', 'title', 'notification_type', 'module', 'read', 'created_at')
    list_filter = ('notification_type', 'module', 'read', 'priority', 'created_at')
    search_fields = ('title', 'message', 'user__username', 'user__email')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'

secure_admin_site.register(Notification, NotificationAdmin)

class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'tenant', 'email_enabled', 'sms_enabled', 'push_enabled', 'updated_at')
    list_filter = ('email_enabled', 'sms_enabled', 'push_enabled', 'tenant')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')

secure_admin_site.register(NotificationPreference, NotificationPreferenceAdmin)

class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'module', 'notification_type', 'is_active', 'created_at')
    list_filter = ('module', 'notification_type', 'is_active')
    search_fields = ('name', 'title_template', 'message_template')

secure_admin_site.register(NotificationTemplate, NotificationTemplateAdmin)

class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'notification', 'delivery_method', 'status', 'created_at')
    list_filter = ('delivery_method', 'status', 'created_at')
    search_fields = ('notification__title', 'error_message')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'

secure_admin_site.register(NotificationLog, NotificationLogAdmin)

# Plan Admin
class PlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'billing_cycle', 'max_users', 'storage_limit_mb', 'popular')
    list_filter = ('billing_cycle', 'popular')
    search_fields = ('name', 'description')

secure_admin_site.register(Plan, PlanAdmin)

# TicketSLA Admin
class TicketSLAAdmin(admin.ModelAdmin):
    list_display = ('id', 'tenant', 'category', 'priority', 'first_response_hours', 'resolution_hours', 'is_active')
    list_filter = ('category', 'priority', 'is_active', 'tenant')
    search_fields = ('tenant__name',)

secure_admin_site.register(TicketSLA, TicketSLAAdmin)