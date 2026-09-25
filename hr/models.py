from django.db import models

from api.models.user import Tenant, UserProfile


class Employee(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='hr_employees')
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    designation = models.CharField(max_length=100, blank=True)
    monthly_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    join_date = models.DateField(null=True, blank=True)
    paid_leave_per_year = models.PositiveIntegerField(default=12)
    is_active = models.BooleanField(default=True)
    user = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='hr_employee')

    class Meta:
        ordering = ['name', 'id']

    def __str__(self):
        return self.name


class LeaveRequest(models.Model):
    TYPES = [('PAID', 'Paid leave'), ('UNPAID', 'Unpaid leave')]
    STATUS = [('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')]
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='hr_leaves')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leaves')
    leave_type = models.CharField(max_length=10, choices=TYPES, default='PAID')
    start_date = models.DateField()
    end_date = models.DateField()
    days = models.PositiveIntegerField(default=1)
    reason = models.CharField(max_length=300, blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default='pending')
    decided_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_date', '-id']


class Payslip(models.Model):
    STATUS = [('draft', 'Draft'), ('paid', 'Paid')]
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='hr_payslips')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='payslips')
    month = models.DateField(help_text='First day of the month')
    gross = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unpaid_days = models.PositiveIntegerField(default=0)
    leave_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    other_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    bonus = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=STATUS, default='draft')
    paid_on = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ('employee', 'month')
        ordering = ['-month', 'employee__name']
