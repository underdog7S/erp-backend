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
    list_display = ('id', 'name', 'email', 'admission_date', 'assigned_class', 'tenant')
    list_filter = ('assigned_class', 'tenant')
    search_fields = ('name', 'email')

admin.site.register(FeeStructure)
admin.site.register(FeePayment)
admin.site.register(FeeDiscount)
admin.site.register(Attendance)
admin.site.register(ReportCard)
admin.site.register(StaffAttendance)

# Register your models here.
