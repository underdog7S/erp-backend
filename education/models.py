from django.db import models
from api.models.user import Tenant, UserProfile

class Class(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    schedule = models.TextField(blank=True)
    def __str__(self):
        return self.name

class Student(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    email = models.EmailField()
    upper_id = models.CharField(max_length=50, help_text="Unique student ID (uppercase).", unique=True, null=True, blank=True)
    admission_date = models.DateField()
    assigned_class = models.ForeignKey(Class, on_delete=models.SET_NULL, null=True, blank=True)
    def __str__(self):
        return self.name

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
    
    class Meta:
        unique_together = ['class_obj', 'fee_type', 'academic_year']
    
    def __str__(self):
        return f"{self.class_obj.name} - {self.fee_type}: ₹{self.amount}"

class FeePayment(models.Model):
    """Individual fee payments made by students"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='fee_payments')
    fee_structure = models.ForeignKey(FeeStructure, on_delete=models.CASCADE)
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
    
    def __str__(self):
        return f"{self.student.name} - {self.fee_structure.fee_type}: ₹{self.amount_paid}"
    
    @property
    def total_amount(self):
        """Total amount including discount"""
        return self.amount_paid + self.discount_amount
    
    @property
    def original_amount(self):
        """Original fee amount without discount"""
        return self.fee_structure.amount

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

class ReportCard(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    term = models.CharField(max_length=50)
    grades = models.TextField(help_text="JSON or CSV of subject:grade")
    generated_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"ReportCard for {self.student.name} - {self.term}"

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
