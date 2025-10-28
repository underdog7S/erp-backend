from rest_framework import serializers
from education.models import Class, Student, FeeStructure, FeePayment, FeeDiscount, Attendance, ReportCard, StaffAttendance, Department
from api.models.user import UserProfile

class ClassSerializer(serializers.ModelSerializer):
    """Serializer for Class model."""
    class Meta:
        model = Class
        fields = ['id', 'name', 'schedule']

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
            'phone', 'address', 'date_of_birth', 'parent_name', 'parent_phone', 'is_active',
            'created_at', 'updated_at'
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
        return data

class FeeStructureSerializer(serializers.ModelSerializer):
    """Serializer for FeeStructure model with validation."""
    class_obj = ClassSerializer(read_only=True)
    class_obj_id = serializers.PrimaryKeyRelatedField(
        queryset=Class.objects.all(), source='class_obj', write_only=True
    )
    
    class Meta:
        model = FeeStructure
        fields = ['id', 'class_obj', 'class_obj_id', 'fee_type', 'amount', 'description', 'is_optional', 'due_date', 'academic_year']
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive.")
        return value

class FeePaymentSerializer(serializers.ModelSerializer):
    """Serializer for FeePayment model with validation."""
    student = StudentSerializer(read_only=True)
    student_id = serializers.PrimaryKeyRelatedField(
        queryset=Student.objects.all(), source='student', write_only=True  # type: ignore
    )
    fee_structure = FeeStructureSerializer(read_only=True)
    fee_structure_id = serializers.PrimaryKeyRelatedField(
        queryset=FeeStructure.objects.all(), source='fee_structure', write_only=True  # type: ignore
    )
    receipt_number = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        model = FeePayment
        fields = ['id', 'student', 'student_id', 'fee_structure', 'fee_structure_id', 'amount_paid', 'payment_date', 'payment_method', 'receipt_number', 'notes', 'discount_amount', 'discount_reason']
    
    def validate_amount_paid(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive.")
        return value
    
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

class ReportCardSerializer(serializers.ModelSerializer):
    student = StudentSerializer(read_only=True)
    student_id = serializers.PrimaryKeyRelatedField(
        queryset=Student.objects.all(), source='student', write_only=True  # type: ignore
    )
    class Meta:
        model = ReportCard
        fields = ['id', 'student', 'student_id', 'term', 'grades', 'generated_at']

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