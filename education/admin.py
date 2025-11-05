from django.contrib import admin
from .models import (
    Department, Class, Student, FeeStructure, FeePayment, FeeDiscount, Attendance, ReportCard, 
    StaffAttendance, StudentPromotion, TransferCertificate, AcademicYear, Term, Subject, Unit,
    AssessmentType, Assessment, MarksEntry, FeeInstallment, FeeInstallmentPlan, 
    AdmissionApplication, BalanceAdjustment, OldBalance,
    Period, Room, Timetable, Holiday, SubstituteTeacher
)
from api.admin_site import secure_admin_site

class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'tenant')

class ClassAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'order', 'next_class', 'tenant', 'schedule')
    list_filter = ('tenant', 'order')
    search_fields = ('name',)
    ordering = ('order', 'name')

class StudentPromotionAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'from_class', 'to_class', 'from_academic_year', 'to_academic_year', 'promotion_type', 'promotion_date', 'promoted_by', 'created_at')
    list_filter = ('promotion_type', 'promotion_date', 'from_academic_year', 'to_academic_year', 'tenant')
    search_fields = ('student__name', 'student__upper_id', 'from_class__name', 'to_class__name')
    readonly_fields = ('created_at',)
    ordering = ('-promotion_date', '-created_at')

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
            'fields': ('parent_name', 'parent_phone', 'father_name', 'father_aadhaar', 'mother_name', 'mother_aadhaar')
        }),
        ('Aadhaar Information', {
            'fields': ('aadhaar_uid',)
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
secure_admin_site.register(StudentPromotion, StudentPromotionAdmin)

class TransferCertificateAdmin(admin.ModelAdmin):
    list_display = ('tc_number', 'student_name', 'class_obj', 'academic_year', 'issue_date', 'dues_paid', 'tenant')
    list_filter = ('academic_year', 'class_obj', 'issue_date', 'dues_paid', 'tenant')
    search_fields = ('tc_number', 'student_name', 'admission_number', 'student__name', 'student__upper_id')
    readonly_fields = ('tc_number', 'created_at', 'updated_at')
    date_hierarchy = 'issue_date'
    fieldsets = (
        ('TC Details', {
            'fields': ('tc_number', 'student', 'academic_year', 'class_obj', 'issue_date', 'last_attended_date', 'reason_for_leaving')
        }),
        ('Student Information (at time of TC)', {
            'fields': ('student_name', 'date_of_birth', 'admission_number', 'admission_date', 'last_class_promoted')
        }),
        ('Fees & Dues', {
            'fields': ('dues_paid', 'dues_details')
        }),
        ('Transfer Details', {
            'fields': ('transferring_to_school', 'transferring_to_address')
        }),
        ('Remarks', {
            'fields': ('conduct_remarks', 'remarks')
        }),
        ('Authority', {
            'fields': ('issued_by', 'approved_by')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    ordering = ('-issue_date', '-created_at')

secure_admin_site.register(TransferCertificate, TransferCertificateAdmin)

class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'is_current', 'tenant')
    list_filter = ('is_current', 'tenant')
    search_fields = ('name',)
    date_hierarchy = 'start_date'
    ordering = ('-start_date',)

class TermAdmin(admin.ModelAdmin):
    list_display = ('name', 'academic_year', 'order', 'start_date', 'end_date', 'is_active', 'tenant')
    list_filter = ('academic_year', 'is_active', 'tenant')
    search_fields = ('name', 'academic_year__name')
    date_hierarchy = 'start_date'
    ordering = ('academic_year', 'order')

class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'class_obj', 'code', 'max_marks', 'weightage', 'has_practical', 'is_active', 'tenant')
    list_filter = ('class_obj', 'has_practical', 'is_active', 'tenant')
    search_fields = ('name', 'code', 'class_obj__name')
    ordering = ('class_obj', 'order', 'name')
    fieldsets = (
        ('Basic Information', {
            'fields': ('tenant', 'class_obj', 'name', 'code', 'order', 'is_active')
        }),
        ('Marks & Weightage', {
            'fields': ('max_marks', 'weightage', 'has_practical', 'practical_max_marks'),
            'description': 'Weightage is used for weighted percentage calculation. Default is 100% (equal weight).'
        }),
    )

class UnitAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject', 'number', 'order', 'is_active', 'tenant')
    list_filter = ('subject', 'is_active', 'tenant')
    search_fields = ('name', 'subject__name')
    ordering = ('subject', 'number')

class AssessmentTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'max_marks', 'weightage', 'order', 'is_active', 'tenant')
    list_filter = ('is_active', 'tenant')
    search_fields = ('name', 'code')
    ordering = ('order', 'name')

class AssessmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject', 'term', 'assessment_type', 'date', 'max_marks', 'passing_marks', 'is_active', 'tenant')
    list_filter = ('term', 'assessment_type', 'is_active', 'tenant')
    search_fields = ('name', 'subject__name', 'term__name')
    date_hierarchy = 'date'
    ordering = ('term', 'subject', 'date')

class MarksEntryAdmin(admin.ModelAdmin):
    list_display = ('student', 'assessment', 'marks_obtained', 'max_marks', 'entered_by', 'entered_at', 'tenant')
    list_filter = ('assessment__term', 'assessment__subject', 'tenant')
    search_fields = ('student__name', 'student__upper_id', 'assessment__name')
    readonly_fields = ('entered_at', 'updated_at')
    date_hierarchy = 'entered_at'
    ordering = ('-entered_at',)

class FeeInstallmentPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'fee_structure', 'number_of_installments', 'installment_type', 'is_active', 'created_at', 'tenant')
    list_filter = ('installment_type', 'is_active', 'tenant')
    search_fields = ('name', 'fee_structure__class_obj__name', 'fee_structure__fee_type')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)

class FeeInstallmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'fee_structure', 'installment_number', 'due_amount', 'paid_amount', 'due_date', 'status', 'tenant')
    list_filter = ('status', 'fee_structure', 'due_date', 'tenant')
    search_fields = ('student__name', 'student__upper_id', 'fee_structure__fee_type')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'due_date'
    ordering = ('fee_structure', 'installment_number')

class AdmissionApplicationAdmin(admin.ModelAdmin):
    list_display = ('applicant_name', 'email', 'phone', 'desired_class', 'status', 'created_at', 'tenant')
    list_filter = ('status', 'desired_class', 'tenant')
    search_fields = ('applicant_name', 'email', 'phone')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)

class BalanceAdjustmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'adjustment_type', 'amount', 'academic_year', 'fee_structure', 'approved_by', 'created_by', 'created_at', 'tenant')
    list_filter = ('adjustment_type', 'academic_year', 'tenant')
    search_fields = ('student__name', 'student__upper_id', 'reason')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)

class OldBalanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'academic_year', 'class_name', 'balance_amount', 'carried_forward_to', 'is_settled', 'settled_date', 'tenant')
    list_filter = ('is_settled', 'academic_year', 'tenant')
    search_fields = ('student__name', 'student__upper_id', 'academic_year')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-academic_year', 'student')

# Register missing models
secure_admin_site.register(AcademicYear, AcademicYearAdmin)
secure_admin_site.register(Term, TermAdmin)
secure_admin_site.register(Subject, SubjectAdmin)
secure_admin_site.register(Unit, UnitAdmin)
secure_admin_site.register(AssessmentType, AssessmentTypeAdmin)
secure_admin_site.register(Assessment, AssessmentAdmin)
secure_admin_site.register(MarksEntry, MarksEntryAdmin)
secure_admin_site.register(FeeInstallmentPlan, FeeInstallmentPlanAdmin)
secure_admin_site.register(FeeInstallment, FeeInstallmentAdmin)
secure_admin_site.register(AdmissionApplication, AdmissionApplicationAdmin)
secure_admin_site.register(BalanceAdjustment, BalanceAdjustmentAdmin)
secure_admin_site.register(OldBalance, OldBalanceAdmin)

# ============================================
# TIMETABLE MANAGEMENT ADMIN
# ============================================

class PeriodAdmin(admin.ModelAdmin):
    list_display = ('name', 'order', 'start_time', 'end_time', 'is_break', 'break_type', 'is_active', 'tenant')
    list_filter = ('is_break', 'break_type', 'is_active', 'tenant')
    search_fields = ('name',)
    ordering = ('order', 'start_time')
    fieldsets = (
        ('Basic Information', {
            'fields': ('tenant', 'name', 'order', 'is_active')
        }),
        ('Time Schedule', {
            'fields': ('start_time', 'end_time')
        }),
        ('Break Settings', {
            'fields': ('is_break', 'break_type'),
            'description': 'Mark as break if this is a recess/lunch/assembly period'
        }),
    )

class RoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'room_number', 'room_type', 'capacity', 'is_active', 'tenant')
    list_filter = ('room_type', 'is_active', 'tenant')
    search_fields = ('name', 'room_number', 'facilities')
    fieldsets = (
        ('Basic Information', {
            'fields': ('tenant', 'name', 'room_number', 'room_type', 'is_active')
        }),
        ('Details', {
            'fields': ('capacity', 'facilities')
        }),
    )

class TimetableAdmin(admin.ModelAdmin):
    list_display = ('class_obj', 'day', 'period', 'subject', 'teacher', 'room', 'is_active', 'academic_year', 'tenant')
    list_filter = ('academic_year', 'class_obj', 'day', 'is_active', 'tenant')
    search_fields = ('class_obj__name', 'subject__name', 'period__name', 'teacher__user__username', 'room__name')
    ordering = ('academic_year', 'class_obj', 'day', 'period__order')
    fieldsets = (
        ('Basic Information', {
            'fields': ('tenant', 'academic_year', 'class_obj', 'day', 'period', 'is_active')
        }),
        ('Scheduling', {
            'fields': ('subject', 'teacher', 'room', 'notes')
        }),
    )
    raw_id_fields = ('teacher', 'subject', 'room')

class HolidayAdmin(admin.ModelAdmin):
    list_display = ('name', 'date', 'holiday_type', 'is_recurring', 'academic_year', 'tenant')
    list_filter = ('holiday_type', 'is_recurring', 'academic_year', 'tenant')
    search_fields = ('name', 'description')
    date_hierarchy = 'date'
    ordering = ('date',)
    fieldsets = (
        ('Basic Information', {
            'fields': ('tenant', 'academic_year', 'name', 'date', 'holiday_type', 'is_recurring')
        }),
        ('Details', {
            'fields': ('description',)
        }),
    )

class SubstituteTeacherAdmin(admin.ModelAdmin):
    list_display = ('timetable', 'date', 'original_teacher', 'substitute_teacher', 'reason', 'is_active', 'tenant')
    list_filter = ('is_active', 'date', 'tenant')
    search_fields = ('timetable__class_obj__name', 'original_teacher__user__username', 'substitute_teacher__user__username', 'reason')
    date_hierarchy = 'date'
    ordering = ('-date', 'timetable')
    raw_id_fields = ('timetable', 'original_teacher', 'substitute_teacher')
    readonly_fields = ('created_at',)

secure_admin_site.register(Period, PeriodAdmin)
secure_admin_site.register(Room, RoomAdmin)
secure_admin_site.register(Timetable, TimetableAdmin)
secure_admin_site.register(Holiday, HolidayAdmin)
secure_admin_site.register(SubstituteTeacher, SubstituteTeacherAdmin)

# Register your models here.
