from django.contrib import admin
from .models import Department, Class, Student, FeeStructure, FeePayment, FeeDiscount, Attendance, ReportCard, StaffAttendance

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'tenant')

@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'tenant', 'schedule')

@admin.register(Student)
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

admin.site.register(FeeStructure)
admin.site.register(FeePayment)
admin.site.register(FeeDiscount)
admin.site.register(Attendance)
admin.site.register(ReportCard)
admin.site.register(StaffAttendance)

# Register your models here.
