from django.db import models

from api.models.user import Tenant, UserProfile


class ExpenseCategory(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='expense_categories')
    name = models.CharField(max_length=100)

    class Meta:
        unique_together = ('tenant', 'name')
        ordering = ['name']

    def __str__(self):
        return self.name


class Expense(models.Model):
    METHODS = [('CASH', 'Cash'), ('UPI', 'UPI'), ('CARD', 'Card'), ('BANK', 'Bank transfer'), ('CHEQUE', 'Cheque')]
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='expenses')
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT, related_name='expenses')
    date = models.DateField()
    vendor = models.CharField(max_length=200, blank=True)
    description = models.CharField(max_length=300, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, help_text='Total paid, including GST')
    gst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text='GST included in the amount (input tax)')
    payment_method = models.CharField(max_length=10, choices=METHODS, default='CASH')
    invoice_number = models.CharField(max_length=60, blank=True, help_text="The supplier's bill number")
    created_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-id']
        indexes = [models.Index(fields=['tenant', 'date'])]

    def __str__(self):
        return f'{self.date} {self.category} {self.amount}'
