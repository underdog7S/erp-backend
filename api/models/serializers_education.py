from rest_framework import serializers
from education.models import (
    Class, Student, FeeStructure, FeePayment, FeeDiscount, Attendance, 
    ReportCard, StaffAttendance, Department, AcademicYear, Term, Subject, 
    Unit, AssessmentType, Assessment, MarksEntry, FeeInstallmentPlan, FeeInstallment,
    OldBalance, BalanceAdjustment, StudentPromotion, TransferCertificate, AdmissionApplication
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
    """Serializer for OldBalance model"""
    student_name = serializers.CharField(source='student.name', read_only=True)
    student_upper_id = serializers.CharField(source='student.upper_id', read_only=True)
    student_class = serializers.CharField(source='student.assigned_class.name', read_only=True)
    
    class Meta:
        model = OldBalance
        fields = [
            'id', 'student', 'student_name', 'student_upper_id', 'student_class',
            'academic_year', 'class_name', 'balance_amount', 'carried_forward_to',
            'is_settled', 'settled_date', 'settlement_payment', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

class BalanceAdjustmentSerializer(serializers.ModelSerializer):
    """Serializer for BalanceAdjustment model"""
    student_name = serializers.CharField(source='student.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.user.get_full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.user.get_full_name', read_only=True)
    
    class Meta:
        model = BalanceAdjustment
        fields = [
            'id', 'student', 'student_name', 'adjustment_type', 'amount', 'reason',
            'academic_year', 'fee_structure', 'approved_by', 'approved_by_name',
            'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by']

class StudentSerializer(serializers.ModelSerializer):
    """Enhanced serializer for Student model with validation."""
    assigned_class = ClassSerializer(read_only=True)
    assigned_class_id = serializers.PrimaryKeyRelatedField(
        queryset=Class.objects.all(), source='assigned_class', write_only=True, required=True
    )
    
    class Meta:
        model = Student
        fields = [
            'id', 'name', 'email', 'upper_id', 'admission_date', 'assigned_class', 'assigned_class_id',
            'phone', 'address', 'date_of_birth', 'gender', 'cast', 'religion', 'parent_name', 'parent_phone',
            'aadhaar_uid', 'father_name', 'father_aadhaar', 'mother_name', 'mother_aadhaar',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def validate_name(self, value):
        if not value:
            raise serializers.ValidationError("Name is required.")
        return value
    
    def validate_email(self, value):
        if not value:
            raise serializers.ValidationError("Email is required.")
        return value
    
    def validate_upper_id(self, value):
        if value:
            # Convert to uppercase for consistency
            value = value.upper()
            # Check if upper_id already exists for this tenant
            if self.instance:
                # For updates, exclude current instance
                existing = Student.objects.filter(upper_id=value, tenant=self.context.get('tenant')).exclude(id=self.instance.id)
            else:
                # For creates, check all instances
                existing = Student.objects.filter(upper_id=value, tenant=self.context.get('tenant'))
            
            if existing.exists():
                raise serializers.ValidationError("A student with this Upper ID already exists.")
        return value
    
    def validate(self, data):
        if not data.get('assigned_class'):
            raise serializers.ValidationError({"assigned_class_id": "Class assignment is required."})
        if not data.get('cast'):
            raise serializers.ValidationError({"cast": "Cast is required."})
        return data

class FeeStructureSerializer(serializers.ModelSerializer):
    """Serializer for FeeStructure model with validation."""
    class_obj = ClassSerializer(read_only=True)
    class_obj_id = serializers.PrimaryKeyRelatedField(
        queryset=Class.objects.all(), source='class_obj', write_only=True
    )
    
    class Meta:
        model = FeeStructure
        fields = ['id', 'class_obj', 'class_obj_id', 'fee_type', 'amount', 'description', 'is_optional', 'due_date', 'academic_year', 'installments_enabled']
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive.")
        return value

class FeeInstallmentPlanSerializer(serializers.ModelSerializer):
    """Serializer for FeeInstallmentPlan model"""
    fee_structure_id = serializers.PrimaryKeyRelatedField(
        queryset=FeeStructure.objects.all(), source='fee_structure', read_only=False, write_only=False
    )
    fee_structure_name = serializers.CharField(source='fee_structure.name', read_only=True, allow_null=True)
    fee_structure_fee_type = serializers.CharField(source='fee_structure.fee_type', read_only=True, allow_null=True)
    
    class Meta:
        model = FeeInstallmentPlan
        fields = [
            'id', 'fee_structure_id', 'fee_structure_name', 'fee_structure_fee_type', 
            'name', 'number_of_installments',
            'installment_type', 'description', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def validate(self, data):
        """Validate installment plan"""
        if data.get('number_of_installments') and data['number_of_installments'] <= 0:
            raise serializers.ValidationError("Number of installments must be positive.")
        return data

class FeeInstallmentSerializer(serializers.ModelSerializer):
    """Serializer for FeeInstallment model"""
    student = StudentSerializer(read_only=True)
    student_id = serializers.PrimaryKeyRelatedField(
        queryset=Student.objects.all(), source='student', write_only=True
    )
    fee_structure_id = serializers.PrimaryKeyRelatedField(
        queryset=FeeStructure.objects.all(), source='fee_structure', read_only=False, write_only=False
    )
    fee_structure_name = serializers.CharField(source='fee_structure.name', read_only=True, allow_null=True)
    fee_structure_amount = serializers.DecimalField(source='fee_structure.amount', max_digits=10, decimal_places=2, read_only=True, allow_null=True)
    installment_plan_id = serializers.PrimaryKeyRelatedField(
        queryset=FeeInstallmentPlan.objects.all(), source='installment_plan', write_only=False, read_only=False, required=False, allow_null=True
    )
    installment_plan_name = serializers.CharField(source='installment_plan.name', read_only=True, allow_null=True)
    remaining_amount = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()
    
    class Meta:
        model = FeeInstallment
        fields = [
            'id', 'student', 'student_id', 
            'fee_structure_id', 'fee_structure_name', 'fee_structure_amount',
            'installment_plan_id', 'installment_plan_name', 
            'installment_number',
            'due_amount', 'paid_amount', 'due_date', 'status', 'late_fee',
            'payment_date', 'notes', 'remaining_amount', 'is_overdue',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['paid_amount', 'status', 'payment_date', 'created_at', 'updated_at', 'remaining_amount', 'is_overdue']

class FeePaymentSerializer(serializers.ModelSerializer):
    """Serializer for FeePayment model with validation and installment support."""
    student = StudentSerializer(read_only=True)
    student_id = serializers.PrimaryKeyRelatedField(
        queryset=Student.objects.all(), source='student', write_only=True  # type: ignore
    )
    fee_structure = FeeStructureSerializer(read_only=True)
    fee_structure_id = serializers.PrimaryKeyRelatedField(
        queryset=FeeStructure.objects.all(), source='fee_structure', write_only=True  # type: ignore
    )
    installment = FeeInstallmentSerializer(read_only=True)
    installment_id = serializers.PrimaryKeyRelatedField(
        queryset=FeeInstallment.objects.all(), source='installment', write_only=True, required=False, allow_null=True  # type: ignore
    )
    receipt_number = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        model = FeePayment
        fields = [
            'id', 'student', 'student_id', 'fee_structure', 'fee_structure_id',
            'installment', 'installment_id', 'amount_paid', 'payment_date',
            'payment_method', 'receipt_number', 'notes', 'discount_amount',
            'discount_reason', 'split_installments'
        ]
    
    def validate_amount_paid(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive.")
        return value
    
    def validate(self, data):
        """Validate payment and installment relationship"""
        installment = data.get('installment')
        split_installments = data.get('split_installments', {})
        
        if installment and split_installments:
            raise serializers.ValidationError("Cannot specify both installment and split_installments.")
        
        if not installment and not split_installments and data.get('fee_structure'):
            # Regular payment without installment - this is fine for backward compatibility
            pass
        
        return data
    
    def create(self, validated_data):
        # Auto-generate receipt number if not provided
        if not validated_data.get('receipt_number'):
            import uuid
            validated_data['receipt_number'] = f"RCP-{uuid.uuid4().hex[:8].upper()}"
        
        # Set collected_by to current user if not provided
        if not validated_data.get('collected_by'):
            request = self.context.get('request')
            if request and request.user:
                try:
                    user_profile = UserProfile._default_manager.get(user=request.user)
                    validated_data['collected_by'] = user_profile
                except Exception:
                    pass  # If user profile doesn't exist, continue without setting collected_by
        
        # Auto-allocate to installments if no explicit installment/split provided
        if not validated_data.get('installment') and not validated_data.get('split_installments'):
            student = validated_data.get('student')
            fee_structure = validated_data.get('fee_structure')
            amount_left = float(validated_data.get('amount_paid') or 0)
            if student and fee_structure and amount_left > 0:
                try:
                    from education.models import FeeInstallment
                    installments = FeeInstallment._default_manager.filter(
                        tenant=student.tenant,
                        student=student,
                        fee_structure=fee_structure
                    ).order_by('due_date', 'id')
                    allocation = {}
                    for inst in installments:
                        if amount_left <= 0:
                            break
                        due_amt = float(inst.due_amount or 0)
                        paid_amt = float(inst.paid_amount or 0)
                        need = max(0.0, due_amt - paid_amt)
                        if need <= 0:
                            continue
                        apply = min(amount_left, need)
                        if apply > 0:
                            allocation[str(inst.id)] = apply
                            amount_left -= apply
                    if allocation:
                        validated_data['split_installments'] = allocation
                except Exception:
                    # If allocation fails, proceed without split
                    pass
        return super().create(validated_data)

class FeeDiscountSerializer(serializers.ModelSerializer):
    """Serializer for FeeDiscount model with validation."""
    class Meta:
        model = FeeDiscount
        fields = ['id', 'name', 'discount_type', 'discount_value', 'applicable_fee_types', 'min_amount', 'max_discount', 'valid_from', 'valid_until', 'is_active', 'description']
    def validate_discount_value(self, value):
        if value < 0:
            raise serializers.ValidationError("Discount value cannot be negative.")
        return value
    def validate_min_amount(self, value):
        if value < 0:
            raise serializers.ValidationError("Minimum amount cannot be negative.")
        return value

class AttendanceSerializer(serializers.ModelSerializer):
    student = StudentSerializer(read_only=True)
    student_id = serializers.PrimaryKeyRelatedField(
        queryset=Student.objects.all(), source='student', write_only=True  # type: ignore
    )
    class Meta:
        model = Attendance
        fields = ['id', 'student', 'student_id', 'date', 'present']

# Academic Structure Serializers
class AcademicYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicYear
        fields = ['id', 'name', 'start_date', 'end_date', 'is_current', 'created_at']
        read_only_fields = ['created_at']

class TermSerializer(serializers.ModelSerializer):
    academic_year = AcademicYearSerializer(read_only=True)
    academic_year_id = serializers.PrimaryKeyRelatedField(
        queryset=AcademicYear.objects.all(), source='academic_year', write_only=True
    )
    
    class Meta:
        model = Term
        fields = ['id', 'academic_year', 'academic_year_id', 'name', 'order', 'start_date', 'end_date', 'is_active']

class SubjectSerializer(serializers.ModelSerializer):
    class_obj = ClassSerializer(read_only=True)
    class_obj_id = serializers.PrimaryKeyRelatedField(
        queryset=Class.objects.all(), source='class_obj', write_only=True
    )
    
    class Meta:
        model = Subject
        fields = [
            'id', 'class_obj', 'class_obj_id', 'name', 'code', 'max_marks', 
            'has_practical', 'practical_max_marks', 'order', 'is_active'
        ]

class UnitSerializer(serializers.ModelSerializer):
    subject = SubjectSerializer(read_only=True)
    subject_id = serializers.PrimaryKeyRelatedField(
        queryset=Subject.objects.all(), source='subject', write_only=True
    )
    
    class Meta:
        model = Unit
        fields = ['id', 'subject', 'subject_id', 'name', 'number', 'description', 'order', 'is_active']

class AssessmentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentType
        fields = ['id', 'name', 'code', 'max_marks', 'weightage', 'order', 'is_active']

class AssessmentSerializer(serializers.ModelSerializer):
    subject = SubjectSerializer(read_only=True)
    subject_id = serializers.PrimaryKeyRelatedField(
        queryset=Subject.objects.all(), source='subject', write_only=True
    )
    term = TermSerializer(read_only=True)
    term_id = serializers.PrimaryKeyRelatedField(
        queryset=Term.objects.all(), source='term', write_only=True
    )
    assessment_type = AssessmentTypeSerializer(read_only=True)
    assessment_type_id = serializers.PrimaryKeyRelatedField(
        queryset=AssessmentType.objects.all(), source='assessment_type', write_only=True
    )
    unit = UnitSerializer(read_only=True)
    unit_id = serializers.PrimaryKeyRelatedField(
        queryset=Unit.objects.all(), source='unit', write_only=True, required=False, allow_null=True
    )
    
    class Meta:
        model = Assessment
        fields = [
            'id', 'subject', 'subject_id', 'term', 'term_id', 'assessment_type', 
            'assessment_type_id', 'unit', 'unit_id', 'name', 'date', 'max_marks', 
            'passing_marks', 'is_active'
        ]

class MarksEntrySerializer(serializers.ModelSerializer):
    student = StudentSerializer(read_only=True)
    student_id = serializers.PrimaryKeyRelatedField(
        queryset=Student.objects.all(), source='student', write_only=True
    )
    assessment = AssessmentSerializer(read_only=True)
    assessment_id = serializers.PrimaryKeyRelatedField(
        queryset=Assessment.objects.all(), source='assessment', write_only=True
    )
    percentage = serializers.ReadOnlyField()
    grade = serializers.ReadOnlyField()
    
    class Meta:
        model = MarksEntry
        fields = [
            'id', 'student', 'student_id', 'assessment', 'assessment_id', 
            'marks_obtained', 'max_marks', 'percentage', 'grade', 'remarks', 
            'entered_at', 'updated_at'
        ]
        read_only_fields = ['entered_at', 'updated_at', 'percentage', 'grade']
    
    def validate_marks_obtained(self, value):
        if value < 0:
            raise serializers.ValidationError("Marks cannot be negative.")
        return value

class ReportCardSerializer(serializers.ModelSerializer):
    """Enhanced ReportCard serializer with full structure"""
    student = StudentSerializer(read_only=True)
    student_id = serializers.PrimaryKeyRelatedField(
        queryset=Student.objects.all(), source='student', write_only=True
    )
    academic_year_id = serializers.PrimaryKeyRelatedField(
        queryset=AcademicYear.objects.all(), source='academic_year', read_only=False, required=False, allow_null=True
    )
    academic_year_name = serializers.CharField(source='academic_year.name', read_only=True, allow_null=True)
    term_id = serializers.PrimaryKeyRelatedField(
        queryset=Term.objects.all(), source='term', read_only=False, required=False, allow_null=True
    )
    term_name = serializers.CharField(source='term.name', read_only=True, allow_null=True)
    class_obj_id = serializers.PrimaryKeyRelatedField(
        queryset=Class.objects.all(), source='class_obj', read_only=False, required=False, allow_null=True
    )
    class_obj_name = serializers.CharField(source='class_obj.name', read_only=True, allow_null=True)
    
    # Legacy fields support
    legacy_term = serializers.CharField(source='old_term', read_only=True)
    legacy_grades = serializers.CharField(source='old_grades', read_only=True)
    
    class Meta:
        model = ReportCard
        fields = [
            'id', 'student', 'student_id', 
            'academic_year_id', 'academic_year_name', 
            'term_id', 'term_name', 
            'class_obj_id', 'class_obj_name',
            'total_marks', 'max_total_marks', 'percentage', 'grade', 'rank_in_class',
            'days_present', 'days_absent', 'attendance_percentage',
            'teacher_remarks', 'principal_remarks', 'conduct_grade',
            'generated_at', 'issued_date', 'updated_at',
            'legacy_term', 'legacy_grades'  # For backward compatibility
        ]
        read_only_fields = [
            'total_marks', 'max_total_marks', 'percentage', 'grade', 
            'days_present', 'days_absent', 'attendance_percentage',
            'generated_at', 'updated_at'
        ]

class StaffAttendanceSerializer(serializers.ModelSerializer):
    staff_id = serializers.PrimaryKeyRelatedField(
        queryset=UserProfile._default_manager.all(),  # Allow all users initially
        source='staff', 
        write_only=True
    )
    staff = serializers.PrimaryKeyRelatedField(read_only=True)
    
    class Meta:
        model = StaffAttendance
        fields = ['id', 'staff', 'staff_id', 'date', 'check_in_time', 'check_out_time']
        extra_kwargs = {
            'date': {'required': True},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        tenant = None
        # Try to get tenant from context (passed from view)
        request = self.context.get('request')
        if request is not None:
            try:
                user = request.user
                profile = UserProfile._default_manager.get(user=user)
                tenant = profile.tenant
            except Exception:
                pass
        fields = getattr(self, 'fields', {})
        if tenant:
            if 'staff_id' in fields:
                fields['staff_id'].queryset = UserProfile._default_manager.filter(tenant=tenant).exclude(role__name='student')
        else:
            if 'staff_id' in fields:
                fields['staff_id'].queryset = UserProfile._default_manager.all()  # Allow all if no tenant context 

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'name']


class TransferCertificateSerializer(serializers.ModelSerializer):
    """Serializer for Transfer Certificate model"""
    student_name_display = serializers.CharField(source='student.name', read_only=True)
    class_name = serializers.CharField(source='class_obj.name', read_only=True)
    academic_year_name = serializers.CharField(source='academic_year.name', read_only=True)
    issued_by_name = serializers.CharField(source='issued_by.user.get_full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.user.get_full_name', read_only=True)
    
    class Meta:
        model = TransferCertificate
        fields = '__all__'
        read_only_fields = ['tc_number', 'created_at', 'updated_at']

class AdmissionApplicationSerializer(serializers.ModelSerializer):
    """Serializer for Admission Application model"""
    desired_class_name = serializers.CharField(source='desired_class.name', read_only=True)
    
    class Meta:
        model = AdmissionApplication
        fields = '__all__'
        read_only_fields = ['created_at'] 