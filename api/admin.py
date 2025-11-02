from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
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
    list_display = ('id', 'get_username', 'get_user_email', 'tenant', 'role', 'department', 'get_assigned_classes')
    search_fields = ('user__username', 'user__email', 'role__name', 'department__name')
    list_filter = ('tenant', 'role', 'department')
    filter_horizontal = ('assigned_classes',)
    fieldsets = (
        (None, {'fields': ('user', 'tenant', 'role', 'department', 'assigned_classes')}),
        ('Personal Info', {'fields': ('photo', 'phone', 'address', 'date_of_birth', 'gender', 'emergency_contact', 'job_title', 'joining_date', 'qualifications', 'bio', 'linkedin')}),
    )
    
    def get_username(self, obj):
        """Display username from User"""
        if obj.user:
            return obj.user.username
        return '-'
    get_username.short_description = 'User'
    get_username.admin_order_field = 'user__username'
    
    def get_user_email(self, obj):
        """Display email from User"""
        if obj.user:
            return obj.user.email
        return '-'
    get_user_email.short_description = 'Email'
    get_user_email.admin_order_field = 'user__email'
    
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
    
    def delete_model(self, request, obj):
        """Override delete to handle user deletion properly"""
        import logging
        from django.db import transaction
        
        logger = logging.getLogger(__name__)
        
        try:
            # Store username for logging before deletion
            username = obj.user.username if obj.user else 'Unknown'
            tenant_name = obj.tenant.name if obj.tenant else 'Unknown'
            user = obj.user
            
            # Use transaction to ensure atomic deletion
            with transaction.atomic():
                # Delete the UserProfile first
                # Note: UserProfile.user has on_delete=CASCADE, so deleting User would auto-delete UserProfile
                # But we delete UserProfile first, then User manually
                obj.delete()
                
                # Now delete the associated User (if it exists and wasn't already deleted)
                if user:
                    try:
                        # Check if user still exists (it might have been deleted by cascade)
                        from django.contrib.auth.models import User as AuthUser
                        if AuthUser.objects.filter(id=user.id).exists():
                            user.delete()
                            logger.info(f"Successfully deleted User '{username}' and UserProfile for tenant '{tenant_name}'")
                        else:
                            logger.info(f"User '{username}' was already deleted (cascade). UserProfile deleted for tenant '{tenant_name}'")
                    except Exception as user_error:
                        logger.warning(f"UserProfile deleted but User deletion failed for '{username}': {user_error}")
                        # Don't raise - UserProfile is already deleted
            
            logger.info(f"Successfully deleted UserProfile for user '{username}' in tenant '{tenant_name}'")
        except Exception as e:
            logger.error(f"Error deleting UserProfile: {type(e).__name__}: {e}", exc_info=True)
            # Re-raise to show error in admin
            raise
    
    def delete_queryset(self, request, queryset):
        """Override bulk delete to handle multiple deletions with per-item error handling"""
        import logging
        from django.db import transaction
        from django.contrib.auth.models import User as AuthUser
        from django.db import connection
        
        logger = logging.getLogger(__name__)
        
        deleted_count = 0
        errors = []
        
        # Check if SupportTicket table exists
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM api_supportticket LIMIT 1")
                support_table_exists = True
        except Exception:
            support_table_exists = False
            logger.warning("SupportTicket table does not exist. Some deletions may fail.")
        
        # Delete each item individually with its own transaction to prevent one failure from breaking all
        for obj in queryset:
            try:
                # Use a separate transaction for each deletion
                with transaction.atomic():
                    username = obj.user.username if obj.user else 'Unknown'
                    tenant_name = obj.tenant.name if obj.tenant else 'Unknown'
                    user = obj.user
                    
                    # If SupportTicket table exists, manually clear foreign key relationships
                    # This prevents the database from trying to update a non-existent relationship
                    if support_table_exists:
                        try:
                            # Use raw SQL to update foreign keys to NULL
                            with connection.cursor() as cursor:
                                cursor.execute(
                                    "UPDATE api_supportticket SET assigned_to_id = NULL WHERE assigned_to_id = %s",
                                    [obj.id]
                                )
                                cursor.execute(
                                    "UPDATE api_ticketsla SET escalation_to_id = NULL WHERE escalation_to_id = %s",
                                    [obj.id]
                                )
                                cursor.execute(
                                    "UPDATE api_tawketointegration SET assign_to_id = NULL WHERE assign_to_id = %s",
                                    [obj.id]
                                )
                        except Exception as fk_error:
                            logger.warning(f"Could not clear foreign keys for UserProfile {obj.id}: {fk_error}")
                    
                    # Delete the UserProfile first
                    obj.delete()
                    
                    # Then delete the associated User (if it still exists)
                    if user:
                        try:
                            if AuthUser.objects.filter(id=user.id).exists():
                                user.delete()
                                logger.info(f"Successfully deleted User '{username}' and UserProfile for tenant '{tenant_name}'")
                            else:
                                logger.info(f"User '{username}' was already deleted (cascade). UserProfile deleted.")
                        except Exception as user_error:
                            logger.warning(f"UserProfile deleted but User deletion failed for '{username}': {user_error}")
                    
                    deleted_count += 1
                    logger.info(f"Successfully deleted UserProfile for user '{username}' in tenant '{tenant_name}'")
            except Exception as e:
                # Capture error but continue with next item
                error_msg = f"Failed to delete {obj}: {str(e)}"
                errors.append(error_msg)
                logger.error(f"Error deleting UserProfile {obj.id}: {type(e).__name__}: {e}", exc_info=True)
                # Don't break the loop - continue with next item
        
        # Show success/error messages
        from django.contrib import messages
        if deleted_count > 0:
            messages.success(request, f"Successfully deleted {deleted_count} user profile(s).")
        if errors:
            messages.error(request, f"Errors occurred: {'; '.join(errors)}")
            if not support_table_exists:
                messages.warning(request, "Note: SupportTicket table does not exist. Please run migrations: python manage.py migrate")
    
    def has_delete_permission(self, request, obj=None):
        """Allow deletion for staff users (can be customized for specific roles)"""
        return request.user.is_staff

# Register with secure admin site instead of default admin
secure_admin_site.register(UserProfile, UserProfileAdmin)

# Custom User Admin to show users in admin
class UserAdmin(DjangoUserAdmin):
    """Custom User admin for secure admin site"""
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'date_joined', 'get_userprofile_info')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    date_hierarchy = 'date_joined'
    ordering = ('username',)
    
    def get_userprofile_info(self, obj):
        """Display UserProfile information"""
        if not obj or not obj.id:
            return "-"
        try:
            profile = UserProfile.objects.get(user=obj)
            return f"{profile.tenant.name} - {profile.role.name if profile.role else 'No Role'}"
        except UserProfile.DoesNotExist:
            return "No Profile"
        except Exception as e:
            return f"Error: {str(e)[:20]}"
    get_userprofile_info.short_description = 'Tenant / Role'
    
    # Override fieldsets for editing
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    # Add fieldsets for creating new users
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'email', 'first_name', 'last_name'),
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser'),
        }),
    )

# Unregister default User admin and register with secure admin site
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass

secure_admin_site.register(User, UserAdmin)

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
    list_display = ('name', 'get_price_display', 'billing_cycle', 'get_users_display', 'get_storage_display', 'popular', 'get_features_summary')
    list_filter = ('billing_cycle', 'popular')
    search_fields = ('name', 'description')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'popular', 'color', 'savings_text'),
            'description': '''
                <div style="background: #e3f2fd; color: #000; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                    <strong style="color: #1976d2;">📋 Plan Basics:</strong>
                    <ul style="margin: 5px 0 0 20px; color: #212121;">
                        <li style="color: #212121;"><strong>Name:</strong> Display name (e.g., "Free", "Starter", "Pro")</li>
                        <li style="color: #212121;"><strong>Description:</strong> Short description shown on pricing page</li>
                        <li style="color: #212121;"><strong>Popular:</strong> Mark as "Most Popular" to highlight on homepage</li>
                        <li style="color: #212121;"><strong>Color:</strong> Hex color code for plan badge (e.g., #2196F3 for blue)</li>
                        <li style="color: #212121;"><strong>Savings Text:</strong> Optional text like "Save ₹2,989 annually"</li>
                    </ul>
                </div>
            '''
        }),
        ('Pricing Configuration', {
            'fields': ('price', 'billing_cycle', 'monthly_equivalent'),
            'description': '''
                <div style="background: #fff3e0; color: #000; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                    <strong style="color: #f57c00;">💰 Pricing Setup:</strong>
                    <ul style="margin: 5px 0 0 20px; color: #212121;">
                        <li style="color: #212121;"><strong>Price:</strong> Amount in ₹ (Indian Rupees). Set to 0 for Free plan, leave blank for Custom pricing</li>
                        <li style="color: #212121;"><strong>Billing Cycle:</strong> Choose Monthly, Annual, or Custom</li>
                        <li style="color: #212121;"><strong>Monthly Equivalent:</strong> If annual, calculate monthly rate (e.g., ₹4,500/year = ₹375/month)</li>
                    </ul>
                    <p style="margin: 10px 0 0 0; color: #212121;"><strong>💡 Tip:</strong> Annual plans should be priced lower than 12x monthly for better value.</p>
                </div>
            '''
        }),
        ('Plan Limits', {
            'fields': ('max_users', 'storage_limit_mb'),
            'description': '''
                <div style="background: #e8f5e9; color: #000; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                    <strong style="color: #388e3c;">📊 Resource Limits:</strong>
                    <ul style="margin: 5px 0 0 20px; color: #212121;">
                        <li style="color: #212121;"><strong>Max Users:</strong> Maximum users allowed. Leave BLANK for unlimited users</li>
                        <li style="color: #212121;"><strong>Storage Limit (MB):</strong> Storage in Megabytes. Examples:
                            <ul style="margin: 5px 0 0 20px; color: #424242;">
                                <li style="color: #424242;">500 MB = 500</li>
                                <li style="color: #424242;">5 GB = 5120 (1024 × 5)</li>
                                <li style="color: #424242;">20 GB = 20480 (1024 × 20)</li>
                                <li style="color: #424242;">50 GB = 51200 (1024 × 50)</li>
                            </ul>
                        </li>
                    </ul>
                    <p style="margin: 10px 0 0 0; color: #212121;"><strong>⚠️ Important:</strong> Storage is in MB. 1 GB = 1024 MB</p>
                </div>
            '''
        }),
        ('Industry Module Access', {
            'fields': (
                'has_education', 'has_pharmacy', 'has_retail', 'has_hotel', 
                'has_restaurant', 'has_salon', 'has_healthcare'
            ),
            'classes': ('collapse',),
            'description': '''
                <div style="background: #f3e5f5; color: #000; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                    <strong style="color: #7b1fa2;">🏭 Industry Modules:</strong>
                    <ul style="margin: 5px 0 0 20px; color: #212121;">
                        <li style="color: #212121;"><strong>Education:</strong> School/College management (Students, Classes, Fees, Attendance)</li>
                        <li style="color: #212121;"><strong>Pharmacy:</strong> Medicine inventory, prescriptions, sales</li>
                        <li style="color: #212121;"><strong>Retail:</strong> Multi-warehouse retail/wholesale management</li>
                        <li style="color: #212121;"><strong>Hotel:</strong> Room booking, guest management</li>
                        <li style="color: #212121;"><strong>Restaurant:</strong> Menu, orders, table management</li>
                        <li style="color: #212121;"><strong>Salon:</strong> Services, appointments, stylist management</li>
                        <li style="color: #212121;"><strong>Healthcare:</strong> Patient management, appointments (Future)</li>
                    </ul>
                    <p style="margin: 10px 0 0 0; color: #212121;"><strong>💡 Note:</strong> Most plans allow 1 module. Business/Enterprise can have all.</p>
                </div>
            '''
        }),
        ('Core Features', {
            'fields': (
                'has_dashboard', 'has_analytics', 'has_api_access', 'has_audit_logs',
                'has_priority_support', 'has_phone_support', 'has_white_label',
                'has_onboarding', 'has_sla_support', 'has_daily_backups',
                'has_custom_reports', 'has_billing', 'has_qc', 'has_inventory'
            ),
            'classes': ('collapse',),
            'description': '''
                <div style="background: #e0f2f1; color: #000; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                    <strong style="color: #00796b;">⚙️ Feature Toggles:</strong>
                    <ul style="margin: 5px 0 0 20px; color: #212121;">
                        <li style="color: #212121;"><strong>Dashboard:</strong> Main dashboard access (usually all plans have this)</li>
                        <li style="color: #212121;"><strong>Analytics:</strong> Advanced reporting and analytics</li>
                        <li style="color: #212121;"><strong>API Access:</strong> REST API for integrations</li>
                        <li style="color: #212121;"><strong>Audit Logs:</strong> Track all user actions</li>
                        <li style="color: #212121;"><strong>Priority Support:</strong> Faster response times</li>
                        <li style="color: #212121;"><strong>Phone Support:</strong> Phone/voice support available</li>
                        <li style="color: #212121;"><strong>White Label:</strong> Remove Zenith branding</li>
                        <li style="color: #212121;"><strong>Onboarding:</strong> Dedicated onboarding assistance</li>
                        <li style="color: #212121;"><strong>SLA Support:</strong> Service Level Agreement guarantee</li>
                        <li style="color: #212121;"><strong>Daily Backups:</strong> Automated daily data backups</li>
                        <li style="color: #212121;"><strong>Custom Reports:</strong> Create custom report templates</li>
                        <li style="color: #212121;"><strong>Billing:</strong> Billing management features</li>
                        <li style="color: #212121;"><strong>QC (Quality Control):</strong> Quality control workflows</li>
                        <li style="color: #212121;"><strong>Inventory:</strong> Inventory management (usually enabled by modules)</li>
                    </ul>
                </div>
            '''
        }),
        ('Premium Features', {
            'fields': (
                'has_strategy_call', 'has_future_discount', 'has_new_features_access'
            ),
            'classes': ('collapse',),
            'description': '''
                <div style="background: #fff9c4; color: #000; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                    <strong style="color: #f57f17;">⭐ Premium Add-Ons:</strong>
                    <ul style="margin: 5px 0 0 20px; color: #212121;">
                        <li style="color: #212121;"><strong>Strategy Call:</strong> 1-on-1 consultation call with expert</li>
                        <li style="color: #212121;"><strong>Future Discount:</strong> Discount on future upgrades/add-ons</li>
                        <li style="color: #212121;"><strong>New Features Access:</strong> Early access to new features (beta)</li>
                    </ul>
                    <p style="margin: 10px 0 0 0; color: #212121;"><strong>💡 Tip:</strong> Usually for Business/Enterprise plans only.</p>
                </div>
            '''
        }),
    )
    
    def get_price_display(self, obj):
        """Display price in readable format"""
        if obj.price is None:
            return "Custom Pricing"
        if obj.price == 0:
            return "₹0 (Free)"
        billing_text = "/year" if obj.billing_cycle == 'annual' else "/month"
        return f"₹{obj.price:,.2f}{billing_text}"
    get_price_display.short_description = 'Price'
    
    def get_users_display(self, obj):
        """Display users in readable format"""
        if obj.max_users is None:
            return "Unlimited"
        return f"{obj.max_users} users"
    get_users_display.short_description = 'Users'
    
    def get_storage_display(self, obj):
        """Display storage in readable format (GB)"""
        gb = obj.storage_limit_mb / 1024
        if gb >= 1:
            return f"{gb:.0f} GB ({obj.storage_limit_mb:,} MB)"
        return f"{obj.storage_limit_mb} MB"
    get_storage_display.short_description = 'Storage'
    
    def get_features_summary(self, obj):
        """Show summary of enabled features"""
        features = []
        if obj.has_api_access:
            features.append("API")
        if obj.has_analytics:
            features.append("Analytics")
        if obj.has_priority_support:
            features.append("Priority Support")
        if obj.has_audit_logs:
            features.append("Audit Logs")
        if obj.has_daily_backups:
            features.append("Backups")
        
        # Count enabled modules
        modules = []
        if obj.has_education:
            modules.append("Edu")
        if obj.has_pharmacy:
            modules.append("Pharma")
        if obj.has_retail:
            modules.append("Retail")
        if obj.has_hotel:
            modules.append("Hotel")
        if obj.has_restaurant:
            modules.append("Rest")
        if obj.has_salon:
            modules.append("Salon")
        
        module_text = f"{len(modules)} modules" if modules else "0 modules"
        
        if features:
            return f"{module_text}, {', '.join(features[:3])}"
        return module_text
    get_features_summary.short_description = 'Features'
    
    readonly_fields = ()

secure_admin_site.register(Plan, PlanAdmin)

# TicketSLA Admin
class TicketSLAAdmin(admin.ModelAdmin):
    list_display = ('id', 'tenant', 'category', 'priority', 'first_response_hours', 'resolution_hours', 'is_active')
    list_filter = ('category', 'priority', 'is_active', 'tenant')
    search_fields = ('tenant__name', 'category', 'priority')
    fieldsets = (
        ('Basic Information', {
            'fields': ('tenant', 'category', 'priority', 'is_active'),
            'description': '''
                <div style="background: #e3f2fd; color: #000; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                    <strong style="color: #1976d2;">📋 SLA Configuration:</strong>
                    <ul style="margin: 5px 0 0 20px; color: #212121;">
                        <li style="color: #212121;"><strong>Tenant:</strong> Organization this SLA applies to (auto-set)</li>
                        <li style="color: #212121;"><strong>Category:</strong> Ticket type (Technical, Billing, Feature Request, etc.)</li>
                        <li style="color: #212121;"><strong>Priority:</strong> Ticket priority level (Low, Medium, High, Urgent)</li>
                        <li style="color: #212121;"><strong>Is Active:</strong> Enable/disable this SLA configuration</li>
                    </ul>
                </div>
            '''
        }),
        ('Response Times', {
            'fields': ('first_response_hours', 'resolution_hours'),
            'description': '''
                <div style="background: #fff3e0; color: #000; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                    <strong style="color: #f57c00;">⏱️ Time Limits (in hours):</strong>
                    <ul style="margin: 5px 0 0 20px; color: #212121;">
                        <li style="color: #212121;"><strong>First Response Hours:</strong> Time to send first reply (e.g., 2 hours = respond within 2 hours)</li>
                        <li style="color: #212121;"><strong>Resolution Hours:</strong> Time to resolve ticket completely (e.g., 24 hours = close within 1 day)</li>
                    </ul>
                    <p style="margin: 10px 0 0 0; color: #212121;"><strong>💡 Examples:</strong> Low priority = 24h response, 72h resolution. Urgent = 1h response, 4h resolution.</p>
                </div>
            '''
        }),
        ('Escalation Settings', {
            'fields': ('escalation_hours', 'escalation_to'),
            'description': '''
                <div style="background: #e8f5e9; color: #000; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                    <strong style="color: #388e3c;">🚨 Escalation:</strong>
                    <ul style="margin: 5px 0 0 20px; color: #212121;">
                        <li style="color: #212121;"><strong>Escalation Hours:</strong> When to escalate if not resolved (e.g., 48 hours)</li>
                        <li style="color: #212121;"><strong>Escalate To:</strong> User profile to notify when ticket needs escalation</li>
                    </ul>
                    <p style="margin: 10px 0 0 0; color: #212121;"><strong>💡 Tip:</strong> Leave escalation fields blank if not needed.</p>
                </div>
            '''
        }),
    )
    readonly_fields = ('tenant',)  # Tenant is auto-set, don't allow editing

secure_admin_site.register(TicketSLA, TicketSLAAdmin)