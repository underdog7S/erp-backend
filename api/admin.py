from django.contrib import admin
from api.models.user import UserProfile
from .models.payments import PaymentTransaction

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'tenant', 'role', 'department')
    search_fields = ('user__username', 'user__email', 'role__name', 'department__name')
    list_filter = ('tenant', 'role', 'department')
    filter_horizontal = ('assigned_classes',)
    fieldsets = (
        (None, {'fields': ('user', 'tenant', 'role', 'department', 'assigned_classes')}),
        ('Personal Info', {'fields': ('photo', 'phone', 'address', 'date_of_birth', 'gender', 'emergency_contact', 'job_title', 'joining_date', 'qualifications', 'bio', 'linkedin')}),
    )

admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(PaymentTransaction) 