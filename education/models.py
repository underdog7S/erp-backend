from django.db import models
from django.utils import timezone
from api.models.user import Tenant, UserProfile

class Class(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    schedule = models.TextField(blank=True)
    order = models.IntegerField(default=0, help_text="Class order/sequence (1 for 1st std, 2 for 2nd std, etc.). Used for automatic promotion.")
    next_class = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='previous_classes', help_text="Next class for promotion (optional, if not set, will use order+1)")
    
    class Meta:
        ordering = ['order', 'name']
        unique_together = ['tenant', 'name']
    
    def __str__(self):
        return self.name
    
    def get_next_class(self):
        """Get the next class for promotion"""
        if self.next_class:
            return self.next_class
        
        # Find class with order = self.order + 1 in same tenant
        try:
            return Class._default_manager.get(tenant=self.tenant, order=self.order + 1)
        except Class.DoesNotExist:
            return None
    
    @property
    def is_highest_class(self):
        """Check if this is the highest class (no next class available)"""
        return self.get_next_class() is None

class Student(models.Model):
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ]
    
    CAST_CHOICES = [
        ('General', 'General'),
        ('OBC', 'Other Backward Class (OBC)'),
        ('SC', 'Scheduled Caste (SC)'),
        ('ST', 'Scheduled Tribe (ST)'),
        ('Other', 'Other'),
    ]
    
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    email = models.EmailField()
    upper_id = models.CharField(max_length=50, help_text="Unique student ID (uppercase).", unique=True, null=True, blank=True)
    admission_date = models.DateField()
    assigned_class = models.ForeignKey(Class, on_delete=models.SET_NULL, null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True)
    cast = models.CharField(max_length=20, choices=CAST_CHOICES, default='General', help_text="Student's caste category (required)")
    religion = models.CharField(max_length=100, blank=True, null=True, help_text="Student's religion")
    parent_name = models.CharField(max_length=100, blank=True, null=True)
    parent_phone = models.CharField(max_length=20, blank=True, null=True)
    # Aadhaar and Parent Details
    aadhaar_uid = models.CharField(max_length=12, blank=True, null=True, help_text="Student's Aadhaar UID (12 digits)")
    father_name = models.CharField(max_length=100, blank=True, null=True, help_text="Father's full name")
    father_aadhaar = models.CharField(max_length=12, blank=True, null=True, help_text="Father's Aadhaar UID (12 digits)")
    mother_name = models.CharField(max_length=100, blank=True, null=True, help_text="Mother's full name")
    mother_aadhaar = models.CharField(max_length=12, blank=True, null=True, help_text="Mother's Aadhaar UID (12 digits)")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['upper_id', 'tenant']
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        if not self.upper_id:
            # Auto-generate upper_id if not provided
            self.upper_id = self.generate_upper_id()
        super().save(*args, **kwargs)
    
    def generate_upper_id(self):
        """Generate unique upper_id for the student"""
        import uuid
        from datetime import datetime
        
        # Format: STU-YYYY-XXXX (e.g., STU-2024-1A2B)
        year = datetime.now().year
        unique_part = uuid.uuid4().hex[:4].upper()
        return f"STU-{year}-{unique_part}"
    
    def __str__(self):
        return f"{self.name} ({self.upper_id})"

class AdmissionApplication(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    applicant_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    desired_class = models.ForeignKey(Class, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=[('pending','Pending'),('approved','Approved'),('rejected','Rejected')], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"Application: {self.applicant_name} ({self.status})"

class FeeStructure(models.Model):
    """Fee structure for each class"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    class_obj = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='fee_structures')
    fee_type = models.CharField(max_length=50, choices=[
        ('TUITION', 'Tuition Fee'),
        ('EXAM', 'Examination Fee'),
        ('LIBRARY', 'Library Fee'),
        ('TRANSPORT', 'Transport Fee'),
        ('HOSTEL', 'Hostel Fee'),
        ('OTHER', 'Other Fee'),
    ])
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255, blank=True)
    is_optional = models.BooleanField(default=False)
    due_date = models.DateField(null=True, blank=True)
    academic_year = models.CharField(max_length=20, default='2024-25')
    installments_enabled = models.BooleanField(default=False, help_text="Enable installment payments for this fee")
    
    class Meta:
        unique_together = ['class_obj', 'fee_type', 'academic_year']
    
    def __str__(self):
        return f"{self.class_obj.name} - {self.fee_type}: ₹{self.amount}"

class FeeInstallmentPlan(models.Model):
    """Installment plan for splitting fees into multiple payments"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    fee_structure = models.ForeignKey(FeeStructure, on_delete=models.CASCADE, related_name='installment_plans')
    name = models.CharField(max_length=100, help_text="e.g., '4 Monthly Installments', 'Quarterly Plan'")
    number_of_installments = models.IntegerField(help_text="Total number of installments")
    installment_type = models.CharField(max_length=20, choices=[
        ('EQUAL', 'Equal Amounts'),
        ('CUSTOM', 'Custom Amounts'),
        ('PERCENTAGE', 'Percentage Based'),
    ], default='EQUAL')
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['tenant', 'fee_structure']  # One plan per fee structure
    
    def __str__(self):
        return f"{self.fee_structure} - {self.name}"
    
    def validate_installments_sum(self, installment_amounts):
        """Validate that installment amounts sum to fee structure amount"""
        total = sum(installment_amounts)
        return abs(total - float(self.fee_structure.amount)) < 0.01  # Allow for rounding

class FeeInstallment(models.Model):
    """Individual installment for a student"""
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PARTIAL', 'Partially Paid'),
        ('PAID', 'Paid'),
        ('OVERDUE', 'Overdue'),
    ]
    
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='fee_installments')
    fee_structure = models.ForeignKey(FeeStructure, on_delete=models.CASCADE, related_name='installments')
    installment_plan = models.ForeignKey(FeeInstallmentPlan, on_delete=models.SET_NULL, null=True, blank=True)
    installment_number = models.IntegerField(help_text="Installment number (1, 2, 3...)")
    due_amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Amount due for this installment")
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Amount paid so far")
    due_date = models.DateField(help_text="Due date for payment")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    late_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Late fee charged if overdue")
    payment_date = models.DateField(null=True, blank=True, help_text="Date when fully paid")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    academic_year = models.CharField(max_length=20, blank=True, null=True, help_text="Academic year for this installment")
    
    class Meta:
        unique_together = ['tenant', 'student', 'fee_structure', 'installment_number']
        ordering = ['fee_structure', 'installment_number']
    
    def __str__(self):
        return f"{self.student.name} - {self.fee_structure.fee_type} Installment {self.installment_number}"
    
    def save(self, *args, **kwargs):
        """Auto-set academic year from fee_structure if not provided"""
        if not self.academic_year and self.fee_structure:
            self.academic_year = self.fee_structure.academic_year
        super().save(*args, **kwargs)
    
    @property
    def remaining_amount(self):
        """Calculate remaining amount to be paid"""
        return self.due_amount - self.paid_amount + self.late_fee
    
    @property
    def is_overdue(self):
        """Check if installment is overdue"""
        from django.utils import timezone
        return self.status != 'PAID' and timezone.now().date() > self.due_date
    
    def update_status(self):
        """Auto-update status based on payment and dates"""
        from django.utils import timezone
        from datetime import date
        today = timezone.now().date()
        # Coerce due_date to date if it was stored as string by older code
        if isinstance(self.due_date, str):
            try:
                self.due_date = date.fromisoformat(self.due_date)
            except Exception:
                pass
        
        if self.paid_amount >= self.due_amount:
            self.status = 'PAID'
            if not self.payment_date:
                self.payment_date = today
        elif self.paid_amount > 0:
            self.status = 'PARTIAL'
        elif today > self.due_date:
            self.status = 'OVERDUE'
        else:
            self.status = 'PENDING'
        
        self.save()

class FeePayment(models.Model):
    """Individual fee payments made by students"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='fee_payments')
    fee_structure = models.ForeignKey(FeeStructure, on_delete=models.CASCADE)
    installment = models.ForeignKey(FeeInstallment, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments', help_text="If payment is for specific installment")
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_reason = models.CharField(max_length=255, blank=True)
    payment_date = models.DateField(auto_now_add=True)
    payment_method = models.CharField(max_length=50, choices=[
        ('CASH', 'Cash'),
        ('CHEQUE', 'Cheque'),
        ('ONLINE', 'Online Transfer'),
        ('CARD', 'Card Payment'),
        ('UPI', 'UPI'),
        ('RAZORPAY', 'Razorpay'),
    ], default='CASH')
    receipt_number = models.CharField(max_length=50, unique=True)
    collected_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)
    split_installments = models.JSONField(default=dict, blank=True, help_text="If payment covers multiple installments: {installment_id: amount}")
    
    def __str__(self):
        if self.installment:
            return f"{self.student.name} - {self.fee_structure.fee_type} Installment {self.installment.installment_number}: ₹{self.amount_paid}"
        return f"{self.student.name} - {self.fee_structure.fee_type}: ₹{self.amount_paid}"
    
    @property
    def total_amount(self):
        """Total amount including discount"""
        return self.amount_paid + self.discount_amount
    
    @property
    def original_amount(self):
        """Original fee amount without discount"""
        return self.fee_structure.amount
    
    academic_year = models.CharField(max_length=20, blank=True, null=True, help_text="Academic year for this payment")
    
    def save(self, *args, **kwargs):
        """Auto-update installment status when payment is saved"""
        # Auto-set academic year from fee_structure if not provided
        if not self.academic_year and self.fee_structure:
            self.academic_year = self.fee_structure.academic_year
        
        super().save(*args, **kwargs)
        # Update installment paid_amount and status
        if self.installment:
            # Recalculate paid_amount from all payments for this installment
            from django.db.models import Sum
            total_paid = FeePayment._default_manager.filter(
                installment=self.installment
            ).aggregate(total=Sum('amount_paid'))['total'] or 0
            self.installment.paid_amount = total_paid
            self.installment.update_status()
        
        # Handle split payments across multiple installments
        if self.split_installments:
            from django.db.models import Sum
            # Use string reference to avoid circular import
            FeeInstallmentModel = self.__class__._meta.apps.get_model('education', 'FeeInstallment')
            for installment_id, amount in self.split_installments.items():
                try:
                    installment = FeeInstallmentModel._default_manager.get(id=installment_id, tenant=self.tenant)
                    # Recalculate total paid from all payments for this installment
                    total_paid = FeePayment._default_manager.filter(
                        installment=installment
                    ).aggregate(total=Sum('amount_paid'))['total'] or 0
                    # Also add amount from split payments
                    split_amount = float(amount) if amount else 0
                    installment.paid_amount = total_paid + split_amount
                    installment.update_status()
                except FeeInstallmentModel.DoesNotExist:
                    pass

class FeeDiscount(models.Model):
    """Discount schemes for fees"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    discount_type = models.CharField(max_length=20, choices=[
        ('PERCENTAGE', 'Percentage'),
        ('FIXED', 'Fixed Amount'),
    ])
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    applicable_fee_types = models.JSONField(default=list)  # List of fee types this discount applies to
    min_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    valid_from = models.DateField()
    valid_until = models.DateField()
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.name} - {self.discount_type} {self.discount_value}"
    
    def calculate_discount(self, amount, fee_type):
        """Calculate discount for given amount and fee type"""
        if not self.is_active or fee_type not in self.applicable_fee_types:
            return 0
        
        if amount < self.min_amount:
            return 0
        
        if self.discount_type == 'PERCENTAGE':
            discount = (amount * self.discount_value) / 100
        else:
            discount = self.discount_value
        
        if self.max_discount:
            discount = min(discount, self.max_discount)
        
        return discount

class Attendance(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    date = models.DateField()
    present = models.BooleanField(default=True)
    def __str__(self):
        return f"{self.student.name} - {self.date}"

# Academic Structure Models
class AcademicYear(models.Model):
    """Academic year (e.g., 2024-25, 2025-26)"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    name = models.CharField(max_length=20, help_text="e.g., 2024-25")
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('tenant', 'name')
        ordering = ['-start_date']
    
    def __str__(self):
        return self.name

class Term(models.Model):
    """Academic terms (Term 1, Term 2, Term 3)"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name='terms')
    name = models.CharField(max_length=50, help_text="e.g., Term 1, Semester 1, Q1")
    order = models.IntegerField(help_text="Display order (1, 2, 3...)")
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('tenant', 'academic_year', 'name')
        ordering = ['academic_year', 'order']
    
    def __str__(self):
        return f"{self.academic_year.name} - {self.name}"

class Subject(models.Model):
    """Subjects for each class"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    class_obj = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='subjects')
    name = models.CharField(max_length=100, help_text="e.g., Mathematics, Science, English")
    code = models.CharField(max_length=20, blank=True, help_text="Subject code (e.g., MATH101)")
    max_marks = models.DecimalField(max_digits=10, decimal_places=2, default=100, help_text="Maximum marks for this subject")
    weightage = models.DecimalField(max_digits=5, decimal_places=2, default=100, help_text="Weightage percentage for weighted calculation (e.g., 30 for 30%). Default is 100% (equal weight)")
    has_practical = models.BooleanField(default=False, help_text="Has practical component")
    practical_max_marks = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Maximum practical marks")
    order = models.IntegerField(default=0, help_text="Display order")
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('tenant', 'class_obj', 'name')
        ordering = ['order', 'name']
    
    def __str__(self):
        return f"{self.class_obj.name} - {self.name}"

class Unit(models.Model):
    """Units/Chapters within a subject"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='units')
    name = models.CharField(max_length=200, help_text="e.g., Unit 1: Algebra, Chapter 1: Sets")
    number = models.IntegerField(help_text="Unit number (1, 2, 3...)")
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('tenant', 'subject', 'number')
        ordering = ['subject', 'number']
    
    def __str__(self):
        return f"{self.subject.name} - {self.name}"

class AssessmentType(models.Model):
    """Assessment types (UT1, UT2, PT1, Half-Yearly, Annual, Practical, etc.)"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    name = models.CharField(max_length=50, help_text="e.g., UT1, PT1, Half-Yearly, Annual, Practical")
    code = models.CharField(max_length=20, blank=True, help_text="Short code (e.g., UT1)")
    max_marks = models.DecimalField(max_digits=10, decimal_places=2, default=100)
    weightage = models.DecimalField(max_digits=5, decimal_places=2, default=100, help_text="Weightage percentage (e.g., 30 for 30%)")
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('tenant', 'name')
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name

class Assessment(models.Model):
    """Specific assessment/test for a subject in a term"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='assessments')
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name='assessments')
    assessment_type = models.ForeignKey(AssessmentType, on_delete=models.PROTECT, related_name='assessments')
    unit = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, blank=True, help_text="Optional: if assessment is unit-specific")
    name = models.CharField(max_length=200, help_text="e.g., Mathematics UT1, Science Half-Yearly")
    date = models.DateField(help_text="Assessment date")
    max_marks = models.DecimalField(max_digits=10, decimal_places=2)
    passing_marks = models.DecimalField(max_digits=10, decimal_places=2, default=40)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('tenant', 'subject', 'term', 'assessment_type')
        ordering = ['term', 'subject', 'date']
    
    def __str__(self):
        return f"{self.subject.name} - {self.assessment_type.name} ({self.term.name})"

class MarksEntry(models.Model):
    """Individual marks entry for a student in an assessment"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='marks_entries')
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='marks_entries')
    marks_obtained = models.DecimalField(max_digits=10, decimal_places=2)
    max_marks = models.DecimalField(max_digits=10, decimal_places=2, help_text="Max marks for this specific assessment")
    remarks = models.TextField(blank=True, help_text="Teacher remarks")
    entered_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True)
    entered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('tenant', 'student', 'assessment')
        ordering = ['-entered_at']
    
    @property
    def percentage(self):
        """Calculate percentage"""
        if self.max_marks > 0:
            return (self.marks_obtained / self.max_marks) * 100
        return 0
    
    @property
    def grade(self):
        """Calculate grade based on percentage"""
        pct = self.percentage
        if pct >= 90:
            return 'A+'
        elif pct >= 80:
            return 'A'
        elif pct >= 70:
            return 'B+'
        elif pct >= 60:
            return 'B'
        elif pct >= 50:
            return 'C+'
        elif pct >= 40:
            return 'C'
        else:
            return 'F'
    
    def __str__(self):
        return f"{self.student.name} - {self.assessment.name}: {self.marks_obtained}/{self.max_marks}"

class ReportCard(models.Model):
    """Enhanced report card with structured data"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='report_cards')
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name='report_cards', null=True, blank=True)
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name='report_cards', null=True, blank=True)
    class_obj = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='report_cards', null=True, blank=True)
    
    # Summary data (auto-calculated)
    total_marks = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_total_marks = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    grade = models.CharField(max_length=10, blank=True)
    rank_in_class = models.IntegerField(null=True, blank=True)
    
    # Attendance data
    days_present = models.IntegerField(default=0)
    days_absent = models.IntegerField(default=0)
    attendance_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Remarks
    teacher_remarks = models.TextField(blank=True)
    principal_remarks = models.TextField(blank=True)
    conduct_grade = models.CharField(max_length=10, blank=True, help_text="A+, A, B+, etc.")
    
    # Legacy fields for backward compatibility
    old_term = models.CharField(max_length=50, blank=True, help_text="Legacy term field")
    old_grades = models.TextField(blank=True, help_text="Legacy grades JSON/CSV")
    
    # Timestamps
    generated_at = models.DateTimeField(auto_now_add=True)
    issued_date = models.DateField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('tenant', 'student', 'academic_year', 'term')
        ordering = ['-academic_year', '-term', 'student']
    
    def calculate_totals(self):
        """Auto-calculate total marks, percentage, and grade from marks entries"""
        from django.db.models import Sum, Count
        from django.db.models.functions import Coalesce
        
        # Get marks entries based on calculation scope
        scope = self.tenant.percentage_calculation_scope if hasattr(self.tenant, 'percentage_calculation_scope') else 'TERM_WISE'
        
        if scope == 'ALL_TERMS':
            # Get all marks entries for this student across all terms in the academic year
            marks_entries = MarksEntry._default_manager.filter(
                tenant=self.tenant,
                student=self.student,
                assessment__term__academic_year=self.academic_year
            )
        else:  # TERM_WISE (default)
            # Get all marks entries for this student in this term only
            marks_entries = MarksEntry._default_manager.filter(
                tenant=self.tenant,
                student=self.student,
                assessment__term=self.term
            )
        
        # Filter out excluded subjects if configured
        excluded_subject_ids = self.tenant.percentage_excluded_subjects or []
        if excluded_subject_ids:
            marks_entries = marks_entries.exclude(assessment__subject_id__in=excluded_subject_ids)
        
        # Calculate totals
        self.total_marks = marks_entries.aggregate(
            total=Coalesce(Sum('marks_obtained'), 0)
        )['total'] or 0
        
        self.max_total_marks = marks_entries.aggregate(
            total=Coalesce(Sum('max_marks'), 0)
        )['total'] or 0
        
        # Calculate percentage based on tenant's method
        method = self.tenant.percentage_calculation_method if hasattr(self.tenant, 'percentage_calculation_method') else 'SIMPLE'
        
        if method == 'SUBJECT_WISE':
            # Calculate percentage for each subject, then average
            # Excluded subjects are already filtered out in marks_entries above
            subject_percentages = []
            subjects_in_term = marks_entries.values_list('assessment__subject_id', flat=True).distinct()
            
            for subject_id in subjects_in_term:
                subject_entries = marks_entries.filter(assessment__subject_id=subject_id)
                subject_obtained = subject_entries.aggregate(total=Coalesce(Sum('marks_obtained'), 0))['total'] or 0
                subject_max = subject_entries.aggregate(total=Coalesce(Sum('max_marks'), 0))['total'] or 0
                if subject_max > 0:
                    subject_pct = (subject_obtained / subject_max) * 100
                    subject_percentages.append(subject_pct)
            
            if subject_percentages:
                self.percentage = sum(subject_percentages) / len(subject_percentages)
            else:
                self.percentage = 0
                
        elif method == 'WEIGHTED':
            # Weighted calculation based on subject weightage
            # Calculate weighted average: Sum(subject_percentage * subject_weightage) / Sum(subject_weightage)
            # Excluded subjects are already filtered out in marks_entries above
            from education.models import Subject
            subject_weighted_sum = 0
            total_weightage = 0
            
            subjects_in_term = marks_entries.values_list('assessment__subject_id', flat=True).distinct()
            
            for subject_id in subjects_in_term:
                try:
                    subject = Subject._default_manager.get(id=subject_id, tenant=self.tenant)
                    subject_entries = marks_entries.filter(assessment__subject_id=subject_id)
                    subject_obtained = subject_entries.aggregate(total=Coalesce(Sum('marks_obtained'), 0))['total'] or 0
                    subject_max = subject_entries.aggregate(total=Coalesce(Sum('max_marks'), 0))['total'] or 0
                    
                    if subject_max > 0:
                        subject_pct = (subject_obtained / subject_max) * 100
                        subject_weightage = float(subject.weightage) if hasattr(subject, 'weightage') and subject.weightage else 100.0
                        subject_weighted_sum += subject_pct * subject_weightage
                        total_weightage += subject_weightage
                except Subject.DoesNotExist:
                    # Subject not found, skip it
                    continue
            
            if total_weightage > 0:
                self.percentage = subject_weighted_sum / total_weightage
            else:
                # Fallback to simple if no valid subjects with weightage
                if self.max_total_marks > 0:
                    self.percentage = (self.total_marks / self.max_total_marks) * 100
                else:
                    self.percentage = 0
        else:  # SIMPLE (default)
            # Simple: (Total Marks / Max Marks) × 100
            if self.max_total_marks > 0:
                self.percentage = (self.total_marks / self.max_total_marks) * 100
            else:
                self.percentage = 0
        
        # Apply rounding based on tenant settings
        rounding = self.tenant.percentage_rounding if hasattr(self.tenant, 'percentage_rounding') else 2
        self.percentage = round(float(self.percentage), rounding)
        
        # Calculate grade
        pct = self.percentage
        if pct >= 90:
            self.grade = 'A+'
        elif pct >= 80:
            self.grade = 'A'
        elif pct >= 70:
            self.grade = 'B+'
        elif pct >= 60:
            self.grade = 'B'
        elif pct >= 50:
            self.grade = 'C+'
        elif pct >= 40:
            self.grade = 'C'
        else:
            self.grade = 'F'
        
        # Calculate attendance
        attendances = Attendance._default_manager.filter(
            tenant=self.tenant,
            student=self.student,
            date__gte=self.term.start_date,
            date__lte=self.term.end_date
        )
        total_days = attendances.count()
        self.days_present = attendances.filter(present=True).count()
        self.days_absent = total_days - self.days_present
        if total_days > 0:
            self.attendance_percentage = (self.days_present / total_days) * 100
        
        self.save()
    
    def __str__(self):
        return f"ReportCard: {self.student.name} - {self.academic_year.name} {self.term.name}"

# Removed old ClassFeeStructure model - replaced with FeeStructure model above

class StaffAttendance(models.Model):
    staff = models.ForeignKey('api.UserProfile', on_delete=models.CASCADE, related_name='education_staff_attendance')
    date = models.DateField()
    check_in_time = models.DateTimeField(null=True, blank=True)
    check_out_time = models.DateTimeField(null=True, blank=True)
    tenant = models.ForeignKey('api.Tenant', on_delete=models.CASCADE, related_name='education_staff_attendance')

    class Meta:
        unique_together = ('staff', 'date', 'tenant')

    def __str__(self):
        return f"{self.staff} - {self.date}"  # Optionally add check-in/out info

class Department(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='education_departments')
    name = models.CharField(max_length=100)
    def __str__(self):
        return self.name

class OldBalance(models.Model):
    """Track outstanding balances from previous academic years"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='old_balances')
    academic_year = models.CharField(max_length=20, help_text="Previous academic year (e.g., 2023-24)")
    class_name = models.CharField(max_length=100, help_text="Class name when balance was recorded")
    balance_amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Outstanding balance from previous year")
    carried_forward_to = models.CharField(max_length=20, blank=True, null=True, help_text="New academic year this balance was carried to")
    is_settled = models.BooleanField(default=False, help_text="Whether this old balance has been cleared")
    settled_date = models.DateField(null=True, blank=True)
    settlement_payment = models.ForeignKey('FeePayment', on_delete=models.SET_NULL, null=True, blank=True, related_name='settled_old_balances')
    notes = models.TextField(blank=True, help_text="Notes about this balance")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-academic_year', 'student']
        unique_together = ['tenant', 'student', 'academic_year']
    
    def __str__(self):
        status = "Settled" if self.is_settled else "Outstanding"
        return f"{self.student.name} - {self.academic_year}: ₹{self.balance_amount} ({status})"

class BalanceAdjustment(models.Model):
    """Track balance adjustments, waivers, and corrections"""
    ADJUSTMENT_TYPE_CHOICES = [
        ('WAIVER', 'Fee Waiver'),
        ('DISCOUNT', 'Discount Applied'),
        ('CORRECTION', 'Correction/Adjustment'),
        ('REFUND', 'Refund'),
        ('LATE_FEE_WAIVER', 'Late Fee Waiver'),
        ('OTHER', 'Other'),
    ]
    
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='balance_adjustments')
    adjustment_type = models.CharField(max_length=20, choices=ADJUSTMENT_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Positive for reduction, negative for addition")
    reason = models.TextField(help_text="Reason for adjustment")
    academic_year = models.CharField(max_length=20, blank=True, null=True)
    fee_structure = models.ForeignKey(FeeStructure, on_delete=models.SET_NULL, null=True, blank=True)
    approved_by = models.ForeignKey('api.UserProfile', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_adjustments')
    created_by = models.ForeignKey('api.UserProfile', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_adjustments')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.student.name} - {self.adjustment_type}: ₹{abs(self.amount)}"

class StudentPromotion(models.Model):
    """Track student class promotions"""
    PROMOTION_TYPE_CHOICES = [
        ('PROMOTED', 'Promoted'),
        ('REPEAT', 'Repeat Same Class'),
        ('DEMOTED', 'Demoted'),
    ]
    
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='promotions')
    from_class = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='promotions_from', null=True, blank=True, help_text="Previous class")
    to_class = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='promotions_to', null=True, blank=True, help_text="New class")
    from_academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name='promotions_from', null=True, blank=True)
    to_academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name='promotions_to', null=True, blank=True)
    promotion_type = models.CharField(max_length=20, choices=PROMOTION_TYPE_CHOICES, default='PROMOTED')
    promotion_date = models.DateField(help_text="Date of promotion")
    notes = models.TextField(blank=True, help_text="Additional notes about promotion")
    promoted_by = models.ForeignKey('api.UserProfile', on_delete=models.SET_NULL, null=True, blank=True, related_name='promoted_students')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-promotion_date', '-created_at']
        unique_together = [['tenant', 'student', 'promotion_date', 'from_class']]
    
    def __str__(self):
        return f"{self.student.name} - {self.from_class} to {self.to_class} ({self.promotion_date})"


class TransferCertificate(models.Model):
    """Transfer Certificate (TC) - Year-wise, class-wise data storage"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='transfer_certificates')
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name='transfer_certificates', null=True, blank=True)
    class_obj = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='transfer_certificates', help_text="Class at time of TC issue")
    
    # TC Details
    tc_number = models.CharField(max_length=50, unique=True, help_text="Unique TC number (auto-generated)")
    issue_date = models.DateField(help_text="Date of TC issue")
    reason_for_leaving = models.CharField(max_length=200, blank=True, null=True, help_text="Reason for leaving school")
    last_attended_date = models.DateField(blank=True, null=True, help_text="Last date student attended classes")
    
    # Student Details at time of TC
    student_name = models.CharField(max_length=100, help_text="Student name at time of TC")
    date_of_birth = models.DateField(blank=True, null=True)
    admission_number = models.CharField(max_length=50, blank=True, null=True)
    admission_date = models.DateField(blank=True, null=True, help_text="Original admission date")
    last_class_promoted = models.CharField(max_length=100, blank=True, null=True, help_text="Last class in which student was promoted")
    
    # Fees and Dues
    dues_paid = models.BooleanField(default=True, help_text="Whether all dues are cleared")
    dues_details = models.TextField(blank=True, help_text="Details of any pending dues")
    
    # Transfer Details
    transferring_to_school = models.CharField(max_length=200, blank=True, null=True, help_text="Name of school/college transferring to")
    transferring_to_address = models.TextField(blank=True, help_text="Address of new school")
    
    # Remarks
    remarks = models.TextField(blank=True, help_text="Additional remarks")
    conduct_remarks = models.CharField(max_length=200, blank=True, help_text="Conduct and character remarks")
    
    # Authority
    issued_by = models.ForeignKey('api.UserProfile', on_delete=models.SET_NULL, null=True, blank=True, related_name='issued_tcs', help_text="Admin/Principal who issued TC")
    approved_by = models.ForeignKey('api.UserProfile', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_tcs', help_text="Principal who approved TC")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-issue_date', '-created_at']
        unique_together = [['tenant', 'tc_number']]
    
    def save(self, *args, **kwargs):
        if not self.tc_number:
            # Auto-generate TC number
            self.tc_number = self.generate_tc_number()
        super().save(*args, **kwargs)
    
    def generate_tc_number(self):
        """Generate unique TC number"""
        import uuid
        from datetime import datetime
        
        # Format: TC-YYYY-MMDD-XXXX (e.g., TC-2024-1102-A1B2)
        year = datetime.now().year
        month_day = datetime.now().strftime('%m%d')
        unique_part = uuid.uuid4().hex[:4].upper()
        return f"TC-{year}-{month_day}-{unique_part}"
    
    def __str__(self):
        return f"TC-{self.tc_number} - {self.student_name} ({self.class_obj})"


# ============================================
# TIMETABLE MANAGEMENT SYSTEM
# ============================================

class Period(models.Model):
    """Time periods/slots for timetable (e.g., Period 1: 9:00 AM - 10:00 AM)"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    name = models.CharField(max_length=50, help_text="e.g., Period 1, Period 2, Morning Assembly")
    order = models.IntegerField(help_text="Period order/sequence (1, 2, 3...)")
    start_time = models.TimeField(help_text="Period start time (e.g., 09:00)")
    end_time = models.TimeField(help_text="Period end time (e.g., 10:00)")
    is_break = models.BooleanField(default=False, help_text="Is this a break/recess period?")
    break_type = models.CharField(max_length=20, blank=True, choices=[
        ('recess', 'Recess'),
        ('lunch', 'Lunch Break'),
        ('assembly', 'Assembly'),
        ('other', 'Other'),
    ], help_text="Break type (only if is_break=True)")
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('tenant', 'order', 'start_time')
        ordering = ['order', 'start_time']
    
    def __str__(self):
        if self.is_break:
            return f"{self.name} ({self.start_time.strftime('%I:%M %p')} - {self.end_time.strftime('%I:%M %p')})"
        return f"{self.name}: {self.start_time.strftime('%I:%M %p')} - {self.end_time.strftime('%I:%M %p')}"


class Room(models.Model):
    """Classrooms, Labs, Halls, etc."""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='education_rooms')
    name = models.CharField(max_length=100, help_text="e.g., Room 101, Lab A, Assembly Hall")
    room_number = models.CharField(max_length=50, blank=True, help_text="Room number")
    room_type = models.CharField(max_length=50, choices=[
        ('classroom', 'Classroom'),
        ('lab', 'Laboratory'),
        ('library', 'Library'),
        ('hall', 'Hall'),
        ('computer_lab', 'Computer Lab'),
        ('physics_lab', 'Physics Lab'),
        ('chemistry_lab', 'Chemistry Lab'),
        ('biology_lab', 'Biology Lab'),
        ('other', 'Other'),
    ], default='classroom')
    capacity = models.IntegerField(null=True, blank=True, help_text="Maximum capacity")
    facilities = models.TextField(blank=True, help_text="Available facilities (e.g., Projector, AC, etc.)")
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('tenant', 'name')
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.get_room_type_display()})"


class Timetable(models.Model):
    """Main timetable - Subject-wise, Day-wise, Teacher-wise, Time-wise scheduling"""
    DAY_CHOICES = [
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ]
    
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name='timetables')
    class_obj = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='timetables')
    day = models.CharField(max_length=10, choices=DAY_CHOICES, help_text="Day of the week")
    period = models.ForeignKey(Period, on_delete=models.CASCADE, related_name='timetable_entries')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='timetable_entries')
    teacher = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True, 
                                related_name='timetable_entries', help_text="Assigned teacher")
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True, 
                            related_name='timetable_entries', help_text="Assigned room/classroom")
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, help_text="Additional notes")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('tenant', 'academic_year', 'class_obj', 'day', 'period')
        ordering = ['academic_year', 'class_obj', 'day', 'period__order']
        indexes = [
            models.Index(fields=['tenant', 'academic_year', 'class_obj', 'day']),
            models.Index(fields=['teacher', 'day', 'period']),
            models.Index(fields=['room', 'day', 'period']),
        ]
    
    def __str__(self):
        teacher_name = self.teacher.user.get_full_name() if self.teacher and self.teacher.user else "No Teacher"
        room_name = self.room.name if self.room else "No Room"
        return f"{self.class_obj.name} - {self.get_day_display()} - {self.period.name}: {self.subject.name} ({teacher_name}, {room_name})"
    
    def clean(self):
        """Validate timetable entry"""
        from django.core.exceptions import ValidationError
        
        # Check if subject belongs to the class
        if self.subject.class_obj != self.class_obj:
            raise ValidationError("Subject must belong to the selected class.")
        
        # Check teacher-class assignment (if teacher is assigned)
        if self.teacher:
            if self.teacher.tenant != self.tenant:
                raise ValidationError("Teacher must belong to the same tenant.")
            # Check if teacher is assigned to this class (optional check)
            if hasattr(self.teacher, 'assigned_classes'):
                if self.class_obj not in self.teacher.assigned_classes.all():
                    # This is a warning, not an error - teacher might teach multiple classes
                    pass


class Holiday(models.Model):
    """Holidays that affect timetable"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name='holidays')
    name = models.CharField(max_length=200, help_text="Holiday name (e.g., Diwali, Christmas)")
    date = models.DateField(help_text="Holiday date")
    holiday_type = models.CharField(max_length=50, choices=[
        ('national', 'National Holiday'),
        ('regional', 'Regional Holiday'),
        ('religious', 'Religious Holiday'),
        ('school', 'School Holiday'),
        ('exam', 'Examination Holiday'),
        ('other', 'Other'),
    ], default='school')
    is_recurring = models.BooleanField(default=False, help_text="Recurring holiday (e.g., every year)")
    description = models.TextField(blank=True)
    
    class Meta:
        unique_together = ('tenant', 'academic_year', 'date', 'name')
        ordering = ['date']
    
    def __str__(self):
        return f"{self.name} - {self.date.strftime('%d %b %Y')}"


class SubstituteTeacher(models.Model):
    """Substitute teacher assignments for temporary replacements"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    timetable = models.ForeignKey(Timetable, on_delete=models.CASCADE, related_name='substitutes')
    original_teacher = models.ForeignKey(UserProfile, on_delete=models.CASCADE, 
                                        related_name='original_substitutes', help_text="Original teacher")
    substitute_teacher = models.ForeignKey(UserProfile, on_delete=models.CASCADE,
                                          related_name='substitute_assignments', help_text="Substitute teacher")
    date = models.DateField(help_text="Date when substitute is needed")
    reason = models.CharField(max_length=200, blank=True, help_text="Reason for substitution")
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('timetable', 'date')
        ordering = ['-date', 'timetable']
    
    def __str__(self):
        return f"{self.date} - {self.timetable.class_obj.name} {self.timetable.period.name}: {self.substitute_teacher.user.get_full_name()} (sub for {self.original_teacher.user.get_full_name()})"


# ============================================
# ADVANCED REPORTING SYSTEM
# ============================================

class ReportTemplate(models.Model):
    """Custom report templates for drag-and-drop report builder"""
    REPORT_TYPE_CHOICES = [
        ('student_performance', 'Student Performance'),
        ('class_performance', 'Class Performance'),
        ('attendance', 'Attendance'),
        ('fee_collection', 'Fee Collection'),
        ('comparative', 'Comparative Analysis'),
        ('custom', 'Custom Report'),
    ]
    
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='report_templates')
    name = models.CharField(max_length=200, help_text="Report template name")
    description = models.TextField(blank=True, help_text="Report description")
    report_type = models.CharField(max_length=50, choices=REPORT_TYPE_CHOICES, default='custom')
    
    # Template configuration (JSON field for flexibility)
    template_config = models.JSONField(default=dict, help_text="Drag-and-drop field configuration")
    
    # Filters and parameters
    available_filters = models.JSONField(default=list, help_text="Available filter options")
    default_parameters = models.JSONField(default=dict, help_text="Default parameters for the report")
    
    # Display settings
    is_public = models.BooleanField(default=False, help_text="Can be used by all users")
    created_by = models.ForeignKey('api.UserProfile', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_report_templates')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ('tenant', 'name')
    
    def __str__(self):
        return f"{self.name} ({self.get_report_type_display()})"


class ReportField(models.Model):
    """Fields available for custom reports"""
    FIELD_TYPE_CHOICES = [
        ('text', 'Text'),
        ('number', 'Number'),
        ('percentage', 'Percentage'),
        ('date', 'Date'),
        ('boolean', 'Boolean'),
        ('choice', 'Choice'),
        ('aggregate', 'Aggregate (Sum/Avg/Max/Min)'),
    ]
    
    AGGREGATE_TYPE_CHOICES = [
        ('sum', 'Sum'),
        ('avg', 'Average'),
        ('max', 'Maximum'),
        ('min', 'Minimum'),
        ('count', 'Count'),
    ]
    
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='report_fields')
    name = models.CharField(max_length=100, help_text="Field name (e.g., 'Total Marks', 'Attendance %')")
    field_key = models.CharField(max_length=100, help_text="Internal field key (e.g., 'total_marks', 'attendance_percentage')")
    field_type = models.CharField(max_length=20, choices=FIELD_TYPE_CHOICES, default='number')
    data_source = models.CharField(max_length=100, help_text="Data source model (e.g., 'ReportCard', 'MarksEntry', 'Attendance')")
    data_field = models.CharField(max_length=100, help_text="Model field name (e.g., 'total_marks', 'percentage')")
    
    # For aggregate fields
    aggregate_type = models.CharField(max_length=10, choices=AGGREGATE_TYPE_CHOICES, blank=True, null=True, help_text="Aggregate function if applicable")
    filter_conditions = models.JSONField(default=dict, help_text="Filter conditions for this field")
    
    # Display settings
    display_name = models.CharField(max_length=100, blank=True, help_text="Display name in report")
    format_string = models.CharField(max_length=50, blank=True, help_text="Format string (e.g., '%.2f', '%d')")
    sortable = models.BooleanField(default=True, help_text="Can be sorted in report")
    groupable = models.BooleanField(default=False, help_text="Can be grouped in report")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
        unique_together = ('tenant', 'field_key')
    
    def __str__(self):
        return f"{self.name} ({self.get_field_type_display()})"


# ============================================
# EXAM MANAGEMENT SYSTEM
# ============================================

class Exam(models.Model):
    """Exam types/names (e.g., Mid-Term, Final, Unit Test)"""
    EXAM_TYPE_CHOICES = [
        ('unit_test', 'Unit Test'),
        ('mid_term', 'Mid-Term Exam'),
        ('final', 'Final Exam'),
        ('preliminary', 'Preliminary Exam'),
        ('mock', 'Mock Exam'),
        ('internal', 'Internal Assessment'),
        ('assignment', 'Assignment'),
        ('project', 'Project'),
        ('practical', 'Practical Exam'),
        ('other', 'Other'),
    ]
    
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='exams')
    name = models.CharField(max_length=200, help_text="Exam name (e.g., 'Mid-Term Exam 2025')")
    exam_type = models.CharField(max_length=50, choices=EXAM_TYPE_CHOICES, default='mid_term')
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name='exams')
    term = models.ForeignKey(Term, on_delete=models.SET_NULL, null=True, blank=True, related_name='exams')
    description = models.TextField(blank=True, help_text="Exam description")
    start_date = models.DateField(help_text="Exam start date")
    end_date = models.DateField(help_text="Exam end date")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-start_date', 'name']
        unique_together = ('tenant', 'name', 'academic_year')
    
    def __str__(self):
        return f"{self.name} ({self.academic_year.name})"


class ExamSchedule(models.Model):
    """Individual exam schedule entries (subject-wise, date-wise, time-wise)"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='exam_schedules')
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='schedules')
    class_obj = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='exam_schedules')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='exam_schedules')
    date = models.DateField(help_text="Exam date")
    start_time = models.TimeField(help_text="Exam start time")
    end_time = models.TimeField(help_text="Exam end time")
    duration_minutes = models.IntegerField(help_text="Duration in minutes", null=True, blank=True)
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True, related_name='exam_schedules', help_text="Exam hall/room")
    max_marks = models.DecimalField(max_digits=10, decimal_places=2, default=100, help_text="Maximum marks")
    instructions = models.TextField(blank=True, help_text="Exam instructions for students")
    invigilator = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='invigilated_exams', help_text="Assigned invigilator")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['date', 'start_time', 'class_obj']
        unique_together = ('tenant', 'exam', 'class_obj', 'subject', 'date')
        indexes = [
            models.Index(fields=['tenant', 'exam', 'date']),
            models.Index(fields=['class_obj', 'date']),
            models.Index(fields=['room', 'date', 'start_time']),
        ]
    
    def __str__(self):
        return f"{self.exam.name} - {self.subject.name} ({self.class_obj.name}) - {self.date}"
    
    def save(self, *args, **kwargs):
        # Auto-calculate duration if not provided
        if not self.duration_minutes and self.start_time and self.end_time:
            start_dt = timezone.datetime.combine(self.date, self.start_time)
            end_dt = timezone.datetime.combine(self.date, self.end_time)
            if end_dt > start_dt:
                self.duration_minutes = int((end_dt - start_dt).total_seconds() / 60)
        super().save(*args, **kwargs)


class SeatingArrangement(models.Model):
    """Seating arrangement for exams - assigns students to seats"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='seating_arrangements')
    exam_schedule = models.ForeignKey(ExamSchedule, on_delete=models.CASCADE, related_name='seating_arrangements')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='exam_seating')
    seat_number = models.CharField(max_length=50, help_text="Seat number (e.g., 'A1', 'B5', 'Row 3 Seat 12')")
    row_number = models.IntegerField(null=True, blank=True, help_text="Row number")
    column_number = models.IntegerField(null=True, blank=True, help_text="Column/Seat number in row")
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True, related_name='seating_arrangements', help_text="Exam hall/room (if different from schedule)")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['exam_schedule', 'seat_number']
        unique_together = ('tenant', 'exam_schedule', 'student')
        indexes = [
            models.Index(fields=['exam_schedule', 'seat_number']),
            models.Index(fields=['student', 'exam_schedule']),
        ]
    
    def __str__(self):
        return f"{self.student.name} - {self.exam_schedule.subject.name} - Seat {self.seat_number}"


class HallTicket(models.Model):
    """Hall tickets for students - generated for exams"""
    STATUS_CHOICES = [
        ('generated', 'Generated'),
        ('issued', 'Issued'),
        ('downloaded', 'Downloaded'),
        ('cancelled', 'Cancelled'),
    ]
    
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='hall_tickets')
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='hall_tickets')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='hall_tickets')
    exam_schedule = models.ForeignKey(ExamSchedule, on_delete=models.SET_NULL, null=True, blank=True, related_name='hall_tickets')
    seating_arrangement = models.ForeignKey(SeatingArrangement, on_delete=models.SET_NULL, null=True, blank=True, related_name='hall_tickets')
    ticket_number = models.CharField(max_length=100, unique=True, help_text="Unique hall ticket number")
    issued_date = models.DateField(default=timezone.now, help_text="Date when hall ticket was issued")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='generated')
    photo_verified = models.BooleanField(default=False, help_text="Student photo verified")
    signature_verified = models.BooleanField(default=False, help_text="Student signature verified")
    remarks = models.TextField(blank=True, help_text="Additional remarks")
    generated_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='generated_hall_tickets')
    generated_at = models.DateTimeField(auto_now_add=True)
    downloaded_at = models.DateTimeField(null=True, blank=True, help_text="When student downloaded the ticket")
    
    class Meta:
        ordering = ['-generated_at', 'student']
        unique_together = ('tenant', 'exam', 'student')
        indexes = [
            models.Index(fields=['tenant', 'exam', 'student']),
            models.Index(fields=['ticket_number']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Hall Ticket {self.ticket_number} - {self.student.name} - {self.exam.name}"
    
    def generate_ticket_number(self):
        """Generate unique ticket number"""
        if not self.ticket_number:
            prefix = f"HT{self.exam.exam_type.upper()[:3]}"
            year = self.exam.academic_year.name.replace('-', '')[:4]
            student_id = self.student.upper_id or str(self.student.id).zfill(6)
            base_ticket = f"{prefix}-{year}-{student_id}"
            
            # Check for uniqueness and add suffix if needed
            import random
            ticket_number = base_ticket
            counter = 0
            while HallTicket.objects.filter(ticket_number=ticket_number).exclude(pk=self.pk if self.pk else None).exists():
                counter += 1
                ticket_number = f"{base_ticket}-{counter:03d}"
                if counter > 999:  # Safety limit
                    # Use UUID as fallback
                    import uuid
                    ticket_number = f"{base_ticket}-{str(uuid.uuid4())[:8]}"
                    break
            
            self.ticket_number = ticket_number
        return self.ticket_number
