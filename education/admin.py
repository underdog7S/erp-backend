from django.contrib import admin
from .models import Department, Class, Student, FeeStructure, FeePayment, FeeDiscount, Attendance, ReportCard, StaffAttendance
from api.admin_site import secure_admin_site

class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'tenant')

class ClassAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'tenant', 'schedule')

class StudentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'email', 'upper_id', 'gender', 'cast', 'religion', 'admission_date', 'assigned_class', 'tenant')
    list_filter = ('assigned_class', 'gender', 'cast', 'tenant', 'is_active')
    search_fields = ('name', 'email', 'upper_id', 'phone', 'parent_name', 'parent_phone', 'religion')
    fieldsets = (
        ('Basic Information', {
            'fields': ('tenant', 'name', 'email', 'upper_id', 'gender', 'cast', 'religion', 'admission_date', 'assigned_class', 'is_active')
        }),
        ('Personal Details', {
            'fields': ('phone', 'address', 'date_of_birth')
        }),
        ('Parent/Guardian Information', {
            'fields': ('parent_name', 'parent_phone')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at')

# Register with secure_admin_site
secure_admin_site.register(Department, DepartmentAdmin)
secure_admin_site.register(Class, ClassAdmin)
secure_admin_site.register(Student, StudentAdmin)
secure_admin_site.register(FeeStructure)
secure_admin_site.register(FeePayment)
secure_admin_site.register(FeeDiscount)
secure_admin_site.register(Attendance)
secure_admin_site.register(ReportCard)
secure_admin_site.register(StaffAttendance)

# Register your models here.
