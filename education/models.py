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
        
        # Get all marks entries for this student in this term
        marks_entries = MarksEntry._default_manager.filter(
            tenant=self.tenant,
            student=self.student,
            assessment__term=self.term
        )
        
        # Calculate totals
        self.total_marks = marks_entries.aggregate(
            total=Coalesce(Sum('marks_obtained'), 0)
        )['total'] or 0
        
        self.max_total_marks = marks_entries.aggregate(
            total=Coalesce(Sum('max_marks'), 0)
        )['total'] or 0
        
        # Calculate percentage
        if self.max_total_marks > 0:
            self.percentage = (self.total_marks / self.max_total_marks) * 100
        else:
            self.percentage = 0
        
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
        unique_together = ['tenant', 'student', 'from_academic_year', 'to_academic_year']
    
    def __str__(self):
        from_name = self.from_class.name if self.from_class else "N/A"
        to_name = self.to_class.name if self.to_class else "N/A"
        return f"{self.student.name}: {from_name} → {to_name} ({self.promotion_date})" 
