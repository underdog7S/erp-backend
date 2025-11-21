from rest_framework import serializers
from education.models import (
    Class, Student, FeeStructure, FeePayment, FeeDiscount, Attendance, 
    ReportCard, StaffAttendance, Department, AcademicYear, Term, Subject, 
    Unit, AssessmentType, Assessment, MarksEntry, FeeInstallmentPlan, FeeInstallment,
    OldBalance, BalanceAdjustment, StudentPromotion, TransferCertificate, AdmissionApplication,
    Period, Room, Timetable, Holiday, SubstituteTeacher, ReportTemplate, ReportField,
    Exam, ExamSchedule, SeatingArrangement, HallTicket
)
from api.models.user import UserProfile

class ClassSerializer(serializers.ModelSerializer):
    """Serializer for Class model."""
    next_class_name = serializers.CharField(source='next_class.name', read_only=True)
    
    class Meta:
        model = Class
        fields = ['id', 'name', 'schedule', 'order', 'next_class', 'next_class_name']
        read_only_fields = ['next_class_name']

class OldBalanceSerializer(serializers.ModelSerializer):
    """Serializer for OldBalance model."""
    class Meta:
        model = OldBalance
        fields = ['id', 'student', 'amount', 'description', 'created_at']
        read_only_fields = ['created_at']

class BalanceAdjustmentSerializer(serializers.ModelSerializer):
    """Serializer for BalanceAdjustment model."""
    class Meta:
        model = BalanceAdjustment
        fields = ['id', 'student', 'adjustment_type', 'amount', 'reason', 'created_at']
        read_only_fields = ['created_at']

class StudentSerializer(serializers.ModelSerializer):
    """Serializer for Student model."""
    assigned_class_name = serializers.CharField(source='assigned_class.name', read_only=True)
    assigned_class_id = serializers.IntegerField(source='assigned_class.id', read_only=True)
    
    class Meta:
        model = Student
        fields = [
            'id', 'name', 'email', 'upper_id', 'admission_date', 'assigned_class', 
            'assigned_class_name', 'assigned_class_id', 'phone', 'address', 
            'date_of_birth', 'gender', 'cast', 'religion', 'parent_name', 'parent_phone',
            'aadhaar_uid', 'father_name', 'father_aadhaar', 'mother_name', 'mother_aadhaar'
        ]

class FeeStructureSerializer(serializers.ModelSerializer):
    """Serializer for FeeStructure model."""
    class_name = serializers.CharField(source='class_obj.name', read_only=True)
    
    class Meta:
        model = FeeStructure
        fields = ['id', 'class_obj', 'class_name', 'fee_type', 'amount', 'description', 'is_optional', 'due_date', 'academic_year', 'installments_enabled']
        read_only_fields = ['class_name']

class FeePaymentSerializer(serializers.ModelSerializer):
    """Serializer for FeePayment model."""
    student_name = serializers.CharField(source='student.name', read_only=True)
    student_roll_number = serializers.CharField(source='student.upper_id', read_only=True, allow_null=True)
    class_name = serializers.CharField(source='student.assigned_class.name', read_only=True, allow_null=True)
    fee_type = serializers.CharField(source='fee_structure.fee_type', read_only=True)
    fee_type_display = serializers.CharField(source='fee_structure.get_fee_type_display', read_only=True)
    fee_structure_amount = serializers.DecimalField(source='fee_structure.amount', max_digits=10, decimal_places=2, read_only=True)
    fee_structure_class = serializers.CharField(source='fee_structure.class_obj.name', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    
    class Meta:
        model = FeePayment
        fields = [
            'id', 'student', 'student_name', 'student_roll_number', 'class_name',
            'fee_structure', 'fee_structure_class', 'fee_structure_amount',
            'amount_paid', 'discount_amount', 'discount_reason',
            'payment_date', 'payment_method', 'payment_method_display', 'fee_type', 'fee_type_display',
            'receipt_number', 'notes', 'installment', 'split_installments', 'academic_year', 'collected_by'
        ]
        read_only_fields = ['fee_structure_class', 'fee_structure_amount', 'payment_method_display', 'fee_type', 'fee_type_display', 'receipt_number']

class FeeDiscountSerializer(serializers.ModelSerializer):
    """Serializer for FeeDiscount model."""
    student_name = serializers.CharField(source='student.name', read_only=True)
    
    class Meta:
        model = FeeDiscount
        fields = ['id', 'student', 'student_name', 'fee_structure', 'discount_amount', 
                 'discount_percentage', 'reason', 'created_at']
        read_only_fields = ['created_at']

class AttendanceSerializer(serializers.ModelSerializer):
    """Serializer for Attendance model."""
    student_name = serializers.CharField(source='student.name', read_only=True)
    student_roll_number = serializers.CharField(source='student.upper_id', read_only=True, allow_null=True)
    class_name = serializers.CharField(source='student.assigned_class.name', read_only=True, allow_null=True)
    
    class Meta:
        model = Attendance
        fields = ['id', 'student', 'student_name', 'student_roll_number', 'class_name',
                 'date', 'present']
        read_only_fields = ['student_name', 'student_roll_number', 'class_name']

class ReportCardSerializer(serializers.ModelSerializer):
    """Serializer for ReportCard model."""

    student_name = serializers.CharField(source='student.name', read_only=True)
    student_roll_number = serializers.CharField(source='student.upper_id', read_only=True, allow_null=True)
    class_name = serializers.CharField(source='class_obj.name', read_only=True, allow_null=True)
    academic_year_name = serializers.CharField(source='academic_year.name', read_only=True, allow_null=True)
    term_name = serializers.CharField(source='term.name', read_only=True, allow_null=True)
    teacher_remarks = serializers.CharField(read_only=True)
    principal_remarks = serializers.CharField(read_only=True)
    remarks = serializers.SerializerMethodField()

    class Meta:
        model = ReportCard
        fields = [
            'id', 'student', 'student_name', 'student_roll_number', 'class_obj', 'class_name',
            'academic_year', 'academic_year_name', 'term', 'term_name',
            'total_marks', 'max_total_marks', 'percentage', 'grade', 'rank_in_class',
            'days_present', 'days_absent', 'attendance_percentage', 'conduct_grade',
            'teacher_remarks', 'principal_remarks', 'remarks', 'issued_date', 'generated_at', 'updated_at'
        ]
        read_only_fields = [
            'student_name', 'student_roll_number', 'class_name', 'academic_year_name', 'term_name',
            'generated_at', 'updated_at'
        ]

    def get_remarks(self, obj):
        parts = []
        if getattr(obj, 'teacher_remarks', None):
            parts.append(f"Teacher: {obj.teacher_remarks.strip()}")
        if getattr(obj, 'principal_remarks', None):
            parts.append(f"Principal: {obj.principal_remarks.strip()}")
        return "\n".join(parts) if parts else ""

class StaffAttendanceSerializer(serializers.ModelSerializer):
    """Serializer for StaffAttendance model."""
    staff_name = serializers.SerializerMethodField()
    department_name = serializers.CharField(source='department.name', read_only=True, allow_null=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = StaffAttendance
        fields = [
            'id', 'staff', 'staff_name', 'department', 'department_name',
            'date', 'check_in_time', 'check_out_time', 'status', 'status_display', 'remarks'
        ]
        read_only_fields = ['staff_name', 'department_name', 'status_display']
    
    def get_staff_name(self, obj):
        if obj.staff and obj.staff.user:
            return obj.staff.user.get_full_name() or obj.staff.user.username
        return None

class DepartmentSerializer(serializers.ModelSerializer):
    """Serializer for Department model."""
    class Meta:
        model = Department
        fields = ['id', 'name', 'description', 'head', 'is_active']

class AcademicYearSerializer(serializers.ModelSerializer):
    """Serializer for AcademicYear model."""
    class Meta:
        model = AcademicYear
        fields = ['id', 'name', 'start_date', 'end_date', 'is_current', 'created_at']
        read_only_fields = ['created_at']

class TermSerializer(serializers.ModelSerializer):
    """Serializer for Term model."""
    academic_year_name = serializers.CharField(source='academic_year.name', read_only=True)
    
    class Meta:
        model = Term
        fields = ['id', 'name', 'academic_year', 'academic_year_name', 'start_date', 'end_date', 'order']
        read_only_fields = ['academic_year_name']

class SubjectSerializer(serializers.ModelSerializer):
    """Serializer for Subject model."""
    class_name = serializers.CharField(source='class_obj.name', read_only=True)
    
    class Meta:
        model = Subject
        fields = [
            'id', 'name', 'code', 'class_obj', 'class_name', 'max_marks', 
            'weightage', 'has_practical', 'practical_max_marks', 'order', 'is_active'
        ]
        read_only_fields = ['class_name']

class UnitSerializer(serializers.ModelSerializer):
    """Serializer for Unit model."""
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    
    class Meta:
        model = Unit
        fields = ['id', 'name', 'subject', 'subject_name', 'order', 'is_active']
        read_only_fields = ['subject_name']

class AssessmentTypeSerializer(serializers.ModelSerializer):
    """Serializer for AssessmentType model."""

    class Meta:
        model = AssessmentType
        fields = ['id', 'name', 'code', 'max_marks', 'weightage', 'order', 'is_active']

class AssessmentSerializer(serializers.ModelSerializer):
    """Serializer for Assessment model."""
    term_name = serializers.CharField(source='term.name', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    
    class Meta:
        model = Assessment
        fields = [
            'id', 'name', 'assessment_type', 'term', 'term_name', 'subject', 'subject_name',
            'max_marks', 'date', 'is_active'
        ]
        read_only_fields = ['term_name', 'subject_name']

class MarksEntrySerializer(serializers.ModelSerializer):
    """Serializer for MarksEntry model."""
    student_name = serializers.CharField(source='student.name', read_only=True)
    student_roll_number = serializers.CharField(source='student.upper_id', read_only=True, allow_null=True)
    assessment_name = serializers.CharField(source='assessment.name', read_only=True)
    subject_name = serializers.CharField(source='assessment.subject.name', read_only=True)
    
    class Meta:
        model = MarksEntry
        fields = [
            'id', 'student', 'student_name', 'student_roll_number', 'assessment', 'assessment_name',
            'subject_name', 'marks_obtained', 'max_marks', 'remarks', 'entered_by', 'entered_at', 'updated_at'
        ]
        read_only_fields = ['student_name', 'student_roll_number', 'assessment_name', 'subject_name', 'entered_at', 'updated_at']

class FeeInstallmentPlanSerializer(serializers.ModelSerializer):
    """Serializer for FeeInstallmentPlan model."""

    fee_structure_fee_type = serializers.CharField(source='fee_structure.fee_type', read_only=True)
    fee_structure_amount = serializers.DecimalField(source='fee_structure.amount', max_digits=10, decimal_places=2, read_only=True)
    class_name = serializers.CharField(source='fee_structure.class_obj.name', read_only=True)

    class Meta:
        model = FeeInstallmentPlan
        fields = [
            'id', 'fee_structure', 'fee_structure_fee_type', 'fee_structure_amount', 'class_name',
            'name', 'number_of_installments', 'installment_type', 'description', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['fee_structure_fee_type', 'fee_structure_amount', 'class_name', 'created_at', 'updated_at']

class FeeInstallmentSerializer(serializers.ModelSerializer):
    """Serializer for FeeInstallment model."""

    student_name = serializers.CharField(source='student.name', read_only=True)
    student_info = serializers.SerializerMethodField()
    fee_structure_fee_type = serializers.CharField(source='fee_structure.fee_type', read_only=True)
    fee_structure_class = serializers.CharField(source='fee_structure.class_obj.name', read_only=True)
    installment_plan_name = serializers.CharField(source='installment_plan.name', read_only=True, allow_null=True)
    remaining_amount = serializers.SerializerMethodField()

    class Meta:
        model = FeeInstallment
        fields = [
            'id', 'student', 'student_name', 'student_info',
            'fee_structure', 'fee_structure_fee_type', 'fee_structure_class',
            'installment_plan', 'installment_plan_name',
            'installment_number', 'due_amount', 'paid_amount', 'remaining_amount',
            'due_date', 'status', 'late_fee', 'payment_date', 'notes',
            'academic_year', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'student_name', 'student_info', 'fee_structure_fee_type', 'fee_structure_class',
            'installment_plan_name', 'remaining_amount', 'created_at', 'updated_at'
        ]

    def get_student_info(self, obj):
        student = obj.student
        if not student:
            return None
        assigned_class = None
        if getattr(student, 'assigned_class', None):
            assigned_class = {
                'id': student.assigned_class.id,
                'name': student.assigned_class.name
            }
        return {
            'id': student.id,
            'name': student.name,
            'upper_id': student.upper_id,
            'assigned_class': assigned_class,
            'parent_phone': getattr(student, 'parent_phone', None),
            'parent_name': getattr(student, 'parent_name', None)
        }

    def get_remaining_amount(self, obj):
        due = obj.due_amount or 0
        paid = obj.paid_amount or 0
        return max(float(due) - float(paid), 0)

class StudentPromotionSerializer(serializers.ModelSerializer):
    """Serializer for StudentPromotion model."""
    student_name = serializers.CharField(source='student.name', read_only=True)
    from_class_name = serializers.CharField(source='from_class.name', read_only=True)
    to_class_name = serializers.CharField(source='to_class.name', read_only=True)
    academic_year_name = serializers.CharField(source='academic_year.name', read_only=True)
    
    class Meta:
        model = StudentPromotion
        fields = [
            'id', 'student', 'student_name', 'from_class', 'from_class_name',
            'to_class', 'to_class_name', 'academic_year', 'academic_year_name',
            'promotion_date', 'remarks', 'created_at'
        ]
        read_only_fields = ['student_name', 'from_class_name', 'to_class_name', 'academic_year_name', 'created_at']

class TransferCertificateSerializer(serializers.ModelSerializer):
    """Serializer for TransferCertificate model."""
    student_name = serializers.CharField(source='student.name', read_only=True)
    student_roll_number = serializers.CharField(source='student.upper_id', read_only=True, allow_null=True)
    class_name = serializers.CharField(source='student.assigned_class.name', read_only=True, allow_null=True)
    issued_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = TransferCertificate
        fields = [
            'id', 'student', 'student_name', 'student_roll_number', 'class_name',
            'tc_number', 'issue_date', 'reason_for_leaving', 'remarks', 'issued_by', 'issued_by_name', 'created_at'
        ]
        read_only_fields = ['student_name', 'student_roll_number', 'class_name', 'issued_by_name', 'created_at']
    
    def get_issued_by_name(self, obj):
        if obj.issued_by and obj.issued_by.user:
            return obj.issued_by.user.get_full_name() or obj.issued_by.user.username
        return None

class AdmissionApplicationSerializer(serializers.ModelSerializer):
    """Serializer for AdmissionApplication model."""
    applied_class_name = serializers.CharField(source='applied_class.name', read_only=True, allow_null=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = AdmissionApplication
        fields = [
            'id', 'student_name', 'date_of_birth', 'gender', 'parent_name', 'parent_phone',
            'parent_email', 'applied_class', 'applied_class_name', 'status', 'status_display',
            'remarks', 'created_at'
        ]
        read_only_fields = ['applied_class_name', 'status_display', 'created_at']

class PeriodSerializer(serializers.ModelSerializer):
    """Serializer for Period model"""
    class Meta:
        model = Period
        fields = [
            'id', 'name', 'order', 'start_time', 'end_time', 
            'is_break', 'break_type', 'tenant'
        ]
        read_only_fields = ['tenant']

class RoomSerializer(serializers.ModelSerializer):
    """Serializer for Room model"""
    room_type_display = serializers.CharField(source='get_room_type_display', read_only=True)
    
    class Meta:
        model = Room
        fields = [
            'id', 'name', 'room_number', 'room_type', 'room_type_display',
            'capacity', 'facilities', 'is_active', 'tenant'
        ]
        read_only_fields = ['tenant']

class TimetableSerializer(serializers.ModelSerializer):
    """Serializer for Timetable model"""
    academic_year_name = serializers.CharField(source='academic_year.name', read_only=True)
    class_name = serializers.CharField(source='class_obj.name', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    period_name = serializers.CharField(source='period.name', read_only=True)
    teacher_name = serializers.SerializerMethodField()
    room_name = serializers.CharField(source='room.name', read_only=True, allow_null=True)
    day_display = serializers.CharField(source='get_day_display', read_only=True)
    
    class Meta:
        model = Timetable
        fields = [
            'id', 'academic_year', 'academic_year_name', 'class_obj', 'class_name',
            'day', 'day_display', 'period', 'period_name', 'subject', 'subject_name',
            'teacher', 'teacher_name', 'room', 'room_name', 'is_active', 'notes',
            'created_at', 'updated_at', 'tenant'
        ]
        read_only_fields = ['tenant', 'created_at', 'updated_at']
    
    def get_teacher_name(self, obj):
        if obj.teacher and obj.teacher.user:
            return obj.teacher.user.get_full_name() or obj.teacher.user.username
        return None


class TimetableDetailSerializer(TimetableSerializer):
    """Detailed serializer for Timetable with nested information"""
    pass

class HolidaySerializer(serializers.ModelSerializer):
    """Serializer for Holiday model"""
    holiday_type_display = serializers.CharField(source='get_holiday_type_display', read_only=True)
    
    class Meta:
        model = Holiday
        fields = [
            'id', 'name', 'date', 'holiday_type', 'holiday_type_display',
            'description', 'is_active', 'tenant'
        ]
        read_only_fields = ['tenant']

class SubstituteTeacherSerializer(serializers.ModelSerializer):
    """Serializer for SubstituteTeacher model"""
    timetable_class = serializers.CharField(source='timetable.class_obj.name', read_only=True)
    timetable_period = serializers.CharField(source='timetable.period.name', read_only=True)
    timetable_subject = serializers.CharField(source='timetable.subject.name', read_only=True)
    original_teacher_name = serializers.SerializerMethodField()
    substitute_teacher_name = serializers.SerializerMethodField()
    date_display = serializers.SerializerMethodField()
    
    class Meta:
        model = SubstituteTeacher
        fields = [
            'id', 'timetable', 'timetable_class', 'timetable_period', 'timetable_subject',
            'date', 'date_display', 'original_teacher', 'original_teacher_name',
            'substitute_teacher', 'substitute_teacher_name', 'reason', 'notes',
            'is_active', 'created_at', 'tenant'
        ]
        read_only_fields = ['tenant', 'created_at']
    
    def get_original_teacher_name(self, obj):
        if obj.original_teacher and obj.original_teacher.user:
            return obj.original_teacher.user.get_full_name() or obj.original_teacher.user.username
        return None
    
    def get_substitute_teacher_name(self, obj):
        if obj.substitute_teacher and obj.substitute_teacher.user:
            return obj.substitute_teacher.user.get_full_name() or obj.substitute_teacher.user.username
        return None
    
    def get_date_display(self, obj):
        return obj.date.strftime('%d %b %Y')


# ============================================
# ADVANCED REPORTING SERIALIZERS
# ============================================

class ReportFieldSerializer(serializers.ModelSerializer):
    """Serializer for ReportField model"""
    field_type_display = serializers.CharField(source='get_field_type_display', read_only=True)
    aggregate_type_display = serializers.CharField(source='get_aggregate_type_display', read_only=True, allow_null=True)
    
    class Meta:
        model = ReportField
        fields = [
            'id', 'name', 'field_key', 'field_type', 'field_type_display',
            'data_source', 'data_field', 'aggregate_type', 'aggregate_type_display',
            'filter_conditions', 'display_name', 'format_string',
            'sortable', 'groupable', 'is_active', 'tenant'
        ]
        read_only_fields = ['tenant']


class ReportTemplateSerializer(serializers.ModelSerializer):
    """Serializer for ReportTemplate model"""
    report_type_display = serializers.CharField(source='get_report_type_display', read_only=True)
    created_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = ReportTemplate
        fields = [
            'id', 'name', 'description', 'report_type', 'report_type_display',
            'template_config', 'available_filters', 'default_parameters',
            'is_public', 'created_by', 'created_by_name', 'created_at', 'updated_at',
            'is_active', 'tenant'
        ]
        read_only_fields = ['tenant', 'created_at', 'updated_at']
    
    def get_created_by_name(self, obj):
        if obj.created_by and obj.created_by.user:
            return obj.created_by.user.get_full_name() or obj.created_by.user.username
        return None


class ReportDataSerializer(serializers.Serializer):
    """Serializer for report data requests"""
    template_id = serializers.IntegerField(required=False, allow_null=True)
    fields = serializers.ListField(child=serializers.CharField(), required=True)
    filters = serializers.DictField(required=False, default=dict)
    group_by = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    sort_by = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    limit = serializers.IntegerField(required=False, default=1000)


# ============================================
# EXAM MANAGEMENT SERIALIZERS
# ============================================

class ExamSerializer(serializers.ModelSerializer):
    """Serializer for Exam model"""
    exam_type_display = serializers.CharField(source='get_exam_type_display', read_only=True)
    academic_year_name = serializers.CharField(source='academic_year.name', read_only=True)
    term_name = serializers.CharField(source='term.name', read_only=True, allow_null=True)
    
    class Meta:
        model = Exam
        fields = [
            'id', 'name', 'exam_type', 'exam_type_display', 'academic_year', 'academic_year_name',
            'term', 'term_name', 'description', 'start_date', 'end_date', 'is_active',
            'created_at', 'updated_at', 'tenant'
        ]
        read_only_fields = ['tenant', 'created_at', 'updated_at']
    
    def validate(self, data):
        """Validate exam dates"""
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        # If updating, get existing values if not provided
        if self.instance:
            start_date = start_date or self.instance.start_date
            end_date = end_date or self.instance.end_date
        
        if start_date and end_date:
            if end_date < start_date:
                raise serializers.ValidationError({
                    'end_date': 'End date must be greater than or equal to start date.'
                })
        
        return data


class ExamScheduleSerializer(serializers.ModelSerializer):
    """Serializer for ExamSchedule model"""
    exam_name = serializers.CharField(source='exam.name', read_only=True)
    class_name = serializers.CharField(source='class_obj.name', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    room_name = serializers.CharField(source='room.name', read_only=True, allow_null=True)
    invigilator_name = serializers.SerializerMethodField()
    duration_display = serializers.SerializerMethodField()
    
    class Meta:
        model = ExamSchedule
        fields = [
            'id', 'exam', 'exam_name', 'class_obj', 'class_name', 'subject', 'subject_name',
            'date', 'start_time', 'end_time', 'duration_minutes', 'duration_display',
            'room', 'room_name', 'max_marks', 'instructions', 'invigilator', 'invigilator_name',
            'is_active', 'created_at', 'updated_at', 'tenant'
        ]
        read_only_fields = ['tenant', 'created_at', 'updated_at', 'duration_minutes']
    
    def get_invigilator_name(self, obj):
        if obj.invigilator and obj.invigilator.user:
            return obj.invigilator.user.get_full_name() or obj.invigilator.user.username
        return None
    
    def get_duration_display(self, obj):
        if obj.duration_minutes:
            hours = obj.duration_minutes // 60
            minutes = obj.duration_minutes % 60
            if hours > 0:
                return f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"
            return f"{minutes}m"
        return None
    
    def validate(self, data):
        """Validate exam schedule times"""
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        date = data.get('date')
        
        # If updating, get existing values if not provided
        if self.instance:
            start_time = start_time or self.instance.start_time
            end_time = end_time or self.instance.end_time
            date = date or self.instance.date
        
        if start_time and end_time:
            if end_time <= start_time:
                raise serializers.ValidationError({
                    'end_time': 'End time must be greater than start time.'
                })
        
        if date and start_time and end_time:
            from django.utils import timezone
            from datetime import datetime
            start_dt = timezone.datetime.combine(date, start_time)
            end_dt = timezone.datetime.combine(date, end_time)
            if end_dt <= start_dt:
                raise serializers.ValidationError({
                    'end_time': 'End time must be greater than start time on the same date.'
                })
        
        return data


class SeatingArrangementSerializer(serializers.ModelSerializer):
    """Serializer for SeatingArrangement model"""
    exam_schedule_info = serializers.SerializerMethodField()
    student_name = serializers.CharField(source='student.name', read_only=True)
    student_roll_number = serializers.CharField(source='student.upper_id', read_only=True, allow_null=True)
    room_name = serializers.CharField(source='room.name', read_only=True, allow_null=True)
    
    class Meta:
        model = SeatingArrangement
        fields = [
            'id', 'exam_schedule', 'exam_schedule_info', 'student', 'student_name', 'student_roll_number',
            'seat_number', 'row_number', 'column_number', 'room', 'room_name',
            'is_active', 'created_at', 'updated_at', 'tenant'
        ]
        read_only_fields = ['tenant', 'created_at', 'updated_at']
    
    def get_exam_schedule_info(self, obj):
        if obj.exam_schedule:
            return {
                'id': obj.exam_schedule.id,
                'subject': obj.exam_schedule.subject.name,
                'date': obj.exam_schedule.date.strftime('%Y-%m-%d'),
                'start_time': obj.exam_schedule.start_time.strftime('%H:%M'),
            }
        return None
    
    def validate(self, data):
        """Validate seating arrangement uniqueness"""
        exam_schedule = data.get('exam_schedule')
        student = data.get('student')
        
        # If updating, get existing values if not provided
        if self.instance:
            exam_schedule = exam_schedule or self.instance.exam_schedule
            student = student or self.instance.student
        
        if exam_schedule and student:
            # Get tenant from context if available
            request = self.context.get('request')
            tenant = None
            if request and hasattr(request, 'user') and hasattr(request.user, 'userprofile'):
                tenant = request.user.userprofile.tenant
            elif self.instance:
                tenant = self.instance.tenant

            if tenant:
                # Check for duplicate seating arrangement
                existing = SeatingArrangement.objects.filter(
                    tenant=tenant,
                    exam_schedule=exam_schedule,
                    student=student,
                    is_active=True
                )

                # Exclude current instance if updating
                if self.instance:
                    existing = existing.exclude(id=self.instance.id)

                if existing.exists():
                    raise serializers.ValidationError({
                        'student': 'This student already has a seating arrangement for this exam schedule.'
                    })
        
        return data


class HallTicketSerializer(serializers.ModelSerializer):
    """Serializer for HallTicket model"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    exam_name = serializers.CharField(source='exam.name', read_only=True)
    student_name = serializers.CharField(source='student.name', read_only=True)
    student_roll_number = serializers.CharField(source='student.upper_id', read_only=True, allow_null=True)
    exam_schedule_info = serializers.SerializerMethodField()
    seating_info = serializers.SerializerMethodField()
    generated_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = HallTicket
        fields = [
            'id', 'exam', 'exam_name', 'student', 'student_name', 'student_roll_number',
            'exam_schedule', 'exam_schedule_info', 'seating_arrangement', 'seating_info',
            'ticket_number', 'issued_date', 'status', 'status_display',
            'photo_verified', 'signature_verified', 'remarks',
            'generated_by', 'generated_by_name', 'generated_at', 'downloaded_at', 'tenant'
        ]
        read_only_fields = ['tenant', 'ticket_number', 'generated_at', 'downloaded_at']
    
    def get_exam_schedule_info(self, obj):
        if obj.exam_schedule:
            return {
                'id': obj.exam_schedule.id,
                'subject': obj.exam_schedule.subject.name,
                'date': obj.exam_schedule.date.strftime('%Y-%m-%d'),
                'start_time': obj.exam_schedule.start_time.strftime('%H:%M'),
                'room': obj.exam_schedule.room.name if obj.exam_schedule.room else None,
            }
        return None
    
    def get_seating_info(self, obj):
        if obj.seating_arrangement:
            return {
                'id': obj.seating_arrangement.id,
                'seat_number': obj.seating_arrangement.seat_number,
                'row_number': obj.seating_arrangement.row_number,
                'column_number': obj.seating_arrangement.column_number,
                'room': obj.seating_arrangement.room.name if obj.seating_arrangement.room else None,
            }
        return None
    
    def get_generated_by_name(self, obj):
        if obj.generated_by and obj.generated_by.user:
            return obj.generated_by.user.get_full_name() or obj.generated_by.user.username
        return None
