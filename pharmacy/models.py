from django.db import models
from api.models.user import Tenant, UserProfile

class MedicineCategory(models.Model):
    """Categories for organizing medicines"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.name

class Supplier(models.Model):
    """Medicine suppliers/vendors"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='pharmacy_suppliers')
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    address = models.TextField()
    gst_number = models.CharField(max_length=20, blank=True)
    payment_terms = models.CharField(max_length=100, default='Net 30')
    
    def __str__(self):
        return self.name

class Medicine(models.Model):
    """Medicine/Product information"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    generic_name = models.CharField(max_length=200, blank=True)
    category = models.ForeignKey(MedicineCategory, on_delete=models.SET_NULL, null=True)
    manufacturer = models.CharField(max_length=200)
    strength = models.CharField(max_length=50, blank=True)
    dosage_form = models.CharField(max_length=50, choices=[
        ('TABLET', 'Tablet'),
        ('CAPSULE', 'Capsule'),
        ('SYRUP', 'Syrup'),
        ('INJECTION', 'Injection'),
        ('CREAM', 'Cream'),
        ('OINTMENT', 'Ointment'),
        ('DROPS', 'Drops'),
        ('INHALER', 'Inhaler'),
        ('OTHER', 'Other'),
    ])
    prescription_required = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    side_effects = models.TextField(blank=True)
    storage_conditions = models.CharField(max_length=200, blank=True)
    expiry_alert_days = models.IntegerField(default=30)
    barcode = models.CharField(max_length=100, blank=True, null=True, help_text="Product barcode for scanning")
    
    def __str__(self):
        return f"{self.name} - {self.strength}"

class MedicineBatch(models.Model):
    """Individual batches of medicines"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE, related_name='batches')
    batch_number = models.CharField(max_length=50)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    manufacturing_date = models.DateField()
    expiry_date = models.DateField()
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    mrp = models.DecimalField(max_digits=10, decimal_places=2)
    quantity_received = models.IntegerField()
    quantity_available = models.IntegerField()
    location = models.CharField(max_length=100, blank=True)
    
    class Meta:
        unique_together = ['medicine', 'batch_number', 'tenant']
    
    def __str__(self):
        return f"{self.medicine.name} - Batch {self.batch_number}"
    
    @property
    def is_expired(self):
        from django.utils import timezone
        return self.expiry_date < timezone.now().date()
    
    @property
    def is_expiring_soon(self):
        from django.utils import timezone
        from datetime import timedelta
        return self.expiry_date <= (timezone.now().date() + timedelta(days=self.medicine.expiry_alert_days))

class Customer(models.Model):
    """Pharmacy customers"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='pharmacy_customers')
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    allergies = models.TextField(blank=True)
    medical_history = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class Prescription(models.Model):
    """Customer prescriptions"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='prescriptions')
    doctor_name = models.CharField(max_length=200)
    prescription_date = models.DateField()
    diagnosis = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Prescription for {self.customer.name} - {self.prescription_date}"

class PrescriptionItem(models.Model):
    """Individual medicines in a prescription"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='items')
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100)
    duration = models.CharField(max_length=100)
    quantity = models.IntegerField()
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.medicine.name} - {self.dosage}"

class Sale(models.Model):
    """Pharmacy sales transactions"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='pharmacy_sales')
    invoice_number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True)
    prescription = models.ForeignKey(Prescription, on_delete=models.SET_NULL, null=True, blank=True)
    sale_date = models.DateTimeField(auto_now_add=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50, choices=[
        ('CASH', 'Cash'),
        ('CARD', 'Card'),
        ('UPI', 'UPI'),
        ('CHEQUE', 'Cheque'),
        ('INSURANCE', 'Insurance'),
    ], default='CASH')
    payment_status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('PARTIAL', 'Partial'),
    ], default='PAID')
    sold_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, related_name='pharmacy_sales')
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.total_amount}"

class SaleItem(models.Model):
    """Individual items in a sale"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='pharmacy_sale_items')
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    medicine_batch = models.ForeignKey(MedicineBatch, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.medicine_batch.medicine.name} - {self.quantity}"

class PurchaseOrder(models.Model):
    """Purchase orders for medicines"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='pharmacy_purchase_orders')
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    po_number = models.CharField(max_length=50, unique=True)
    order_date = models.DateField()
    expected_delivery = models.DateField()
    status = models.CharField(max_length=20, choices=[
        ('DRAFT', 'Draft'),
        ('ORDERED', 'Ordered'),
        ('RECEIVED', 'Received'),
        ('CANCELLED', 'Cancelled'),
    ], default='DRAFT')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, related_name='pharmacy_purchase_orders')
    
    def __str__(self):
        return f"PO {self.po_number} - {self.supplier.name}"

class PurchaseOrderItem(models.Model):
    """Items in purchase orders"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='pharmacy_purchase_order_items')
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.medicine.name} - {self.quantity}"

class StockAdjustment(models.Model):
    """Stock adjustments for inventory management"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='pharmacy_stock_adjustments')
    medicine_batch = models.ForeignKey(MedicineBatch, on_delete=models.CASCADE)
    adjustment_type = models.CharField(max_length=20, choices=[
        ('ADD', 'Add'),
        ('REMOVE', 'Remove'),
        ('DAMAGED', 'Damaged'),
        ('EXPIRED', 'Expired'),
        ('THEFT', 'Theft'),
    ])
    quantity = models.IntegerField()
    reason = models.TextField()
    adjustment_date = models.DateTimeField(auto_now_add=True)
    adjusted_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, related_name='pharmacy_stock_adjustments')
    
    def __str__(self):
        return f"{self.medicine_batch.medicine.name} - {self.adjustment_type} {self.quantity}"

class StaffAttendance(models.Model):
    """Staff attendance for pharmacy employees"""
    staff = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='pharmacy_staff_attendance')
    date = models.DateField()
    check_in_time = models.DateTimeField(null=True, blank=True)
    check_out_time = models.DateTimeField(null=True, blank=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='pharmacy_staff_attendance')

    class Meta:
        unique_together = ('staff', 'date', 'tenant')

    def __str__(self):
        return f"{self.staff} - {self.date}" 