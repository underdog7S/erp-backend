from django.db import models
from django.contrib.auth.models import User
from api.models.user import Tenant, UserProfile
from decimal import Decimal
import uuid

class Invoice(models.Model):
    """Invoice model for generating professional invoices"""
    
    INVOICE_STATUS = [
        ('DRAFT', 'Draft'),
        ('SENT', 'Sent'),
        ('PAID', 'Paid'),
        ('OVERDUE', 'Overdue'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    PAYMENT_TERMS = [
        ('IMMEDIATE', 'Immediate'),
        ('NET_7', 'Net 7'),
        ('NET_15', 'Net 15'),
        ('NET_30', 'Net 30'),
        ('NET_45', 'Net 45'),
        ('NET_60', 'Net 60'),
    ]
    
    # Invoice details
    invoice_number = models.CharField(max_length=50, unique=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='invoices')
    
    # Customer information
    customer_name = models.CharField(max_length=200)
    customer_email = models.EmailField()
    customer_address = models.TextField()
    customer_phone = models.CharField(max_length=20, blank=True)
    customer_gstin = models.CharField(max_length=15, blank=True)
    
    # Invoice details
    issue_date = models.DateField()
    due_date = models.DateField()
    payment_terms = models.CharField(max_length=20, choices=PAYMENT_TERMS, default='NET_30')
    status = models.CharField(max_length=20, choices=INVOICE_STATUS, default='DRAFT')
    
    # Financial details
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # Percentage
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Company information
    company_name = models.CharField(max_length=200)
    company_address = models.TextField()
    company_phone = models.CharField(max_length=20, blank=True)
    company_email = models.EmailField(blank=True)
    company_gstin = models.CharField(max_length=15, blank=True)
    company_logo = models.ImageField(upload_to='company_logos/', null=True, blank=True)
    
    # Additional information
    notes = models.TextField(blank=True)
    terms_conditions = models.TextField(blank=True)
    
    # Tracking
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_invoices')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    # PDF generation
    pdf_file = models.FileField(upload_to='invoices/', null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['due_date', 'status']),
            models.Index(fields=['customer_email']),
        ]
    
    def __str__(self):
        return f"Invoice #{self.invoice_number} - {self.customer_name}"
    
    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = self.generate_invoice_number()
        
        # Calculate totals
        self.calculate_totals()
        
        super().save(*args, **kwargs)
    
    def generate_invoice_number(self):
        """Generate unique invoice number"""
        from django.utils import timezone
        
        year = timezone.now().year
        month = timezone.now().month
        
        # Get count of invoices for this month
        count = Invoice.objects.filter(
            created_at__year=year,
            created_at__month=month
        ).count() + 1
        
        return f"INV-{year}{month:02d}-{count:04d}"
    
    def calculate_totals(self):
        """Calculate invoice totals"""
        # Calculate subtotal from items
        self.subtotal = sum(item.total for item in self.items.all())
        
        # Calculate tax
        self.tax_amount = (self.subtotal * self.tax_rate) / 100
        
        # Calculate total
        self.total_amount = self.subtotal + self.tax_amount - self.discount_amount
    
    @property
    def balance_due(self):
        """Calculate remaining balance"""
        return self.total_amount - self.amount_paid
    
    @property
    def is_overdue(self):
        """Check if invoice is overdue"""
        from django.utils import timezone
        return self.status != 'PAID' and timezone.now().date() > self.due_date
    
    @property
    def days_overdue(self):
        """Get days overdue"""
        from django.utils import timezone
        if self.is_overdue:
            return (timezone.now().date() - self.due_date).days
        return 0

class InvoiceItem(models.Model):
    """Individual items in an invoice"""
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    
    description = models.CharField(max_length=500)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Calculated fields
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    class Meta:
        ordering = ['id']
    
    def __str__(self):
        return f"{self.description} - {self.quantity} x ₹{self.unit_price}"
    
    def save(self, *args, **kwargs):
        # Calculate item totals
        self.subtotal = self.quantity * self.unit_price
        self.discount_amount = (self.subtotal * self.discount_percent) / 100
        self.total = self.subtotal - self.discount_amount
        
        super().save(*args, **kwargs)
        
        # Update invoice totals
        self.invoice.calculate_totals()
        self.invoice.save()

class InvoicePayment(models.Model):
    """Payment records for invoices"""
    PAYMENT_METHODS = [
        ('CASH', 'Cash'),
        ('CHEQUE', 'Cheque'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('CREDIT_CARD', 'Credit Card'),
        ('DEBIT_CARD', 'Debit Card'),
        ('UPI', 'UPI'),
        ('RAZORPAY', 'Razorpay'),
        ('OTHER', 'Other'),
    ]
    
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    payment_date = models.DateField()
    reference_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Payment of ₹{self.amount} for {self.invoice.invoice_number}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Update invoice paid amount
        self.invoice.amount_paid = sum(payment.amount for payment in self.invoice.payments.all())
        
        # Update invoice status
        if self.invoice.amount_paid >= self.invoice.total_amount:
            self.invoice.status = 'PAID'
            from django.utils import timezone
            self.invoice.paid_at = timezone.now()
        
        self.invoice.save()

class InvoiceTemplate(models.Model):
    """Invoice templates for different tenants"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='invoice_templates')
    
    name = models.CharField(max_length=100)
    is_default = models.BooleanField(default=False)
    
    # Template settings
    template_color = models.CharField(max_length=7, default='#1976d2')  # Hex color
    show_logo = models.BooleanField(default=True)
    show_tax = models.BooleanField(default=True)
    show_discount = models.BooleanField(default=True)
    
    # Header/Footer
    header_text = models.TextField(blank=True)
    footer_text = models.TextField(blank=True)
    
    # Terms and conditions
    default_terms = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['tenant', 'name']
    
    def __str__(self):
        return f"{self.tenant.name} - {self.name}"
    
    def save(self, *args, **kwargs):
        # Ensure only one default template per tenant
        if self.is_default:
            InvoiceTemplate.objects.filter(tenant=self.tenant, is_default=True).update(is_default=False)
        super().save(*args, **kwargs) 