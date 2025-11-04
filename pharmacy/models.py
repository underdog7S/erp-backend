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
    loyalty_points = models.IntegerField(default=0, help_text="Current available loyalty points")
    total_points_earned = models.IntegerField(default=0, help_text="Lifetime points earned")
    total_points_redeemed = models.IntegerField(default=0, help_text="Lifetime points redeemed")
    loyalty_enrolled = models.BooleanField(default=True, help_text="Whether customer is enrolled in loyalty program")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    def calculate_loyalty_points(self, sale_amount, points_per_rupee=1):
        """Calculate loyalty points for a sale amount"""
        return int(sale_amount * points_per_rupee)
    
    def add_loyalty_points(self, points, sale=None, description=""):
        """Add loyalty points to customer"""
        from django.utils import timezone
        from datetime import timedelta
        
        self.loyalty_points += points
        self.total_points_earned += points
        self.save()
        
        # Create transaction record
        expiry_date = timezone.now().date() + timedelta(days=365) if points > 0 else None  # Points expire in 1 year
        LoyaltyTransaction.objects.create(
            tenant=self.tenant,
            customer=self,
            transaction_type='EARNED',
            points=points,
            sale=sale,
            description=description or f"Points earned from sale",
            expiry_date=expiry_date
        )
    
    def redeem_loyalty_points(self, points, reward=None, description=""):
        """Redeem loyalty points from customer"""
        if points > self.loyalty_points:
            raise ValueError("Insufficient loyalty points")
        
        self.loyalty_points -= points
        self.total_points_redeemed += points
        self.save()
        
        # Create transaction record
        LoyaltyTransaction.objects.create(
            tenant=self.tenant,
            customer=self,
            transaction_type='REDEEMED',
            points=-points,
            reward=reward,
            description=description or f"Points redeemed",
        )

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

class SaleReturn(models.Model):
    """Return/exchange/refund for pharmacy sales"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='pharmacy_sale_returns')
    return_number = models.CharField(max_length=50, unique=True)
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='returns')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='returns')
    return_date = models.DateTimeField(auto_now_add=True)
    return_type = models.CharField(max_length=20, choices=[
        ('RETURN', 'Return'),
        ('EXCHANGE', 'Exchange'),
        ('REFUND', 'Refund'),
    ], default='RETURN')
    return_reason = models.CharField(max_length=100, choices=[
        ('DAMAGED', 'Damaged Product'),
        ('EXPIRED', 'Expired Product'),
        ('WRONG_ITEM', 'Wrong Item'),
        ('DEFECTIVE', 'Defective'),
        ('CUSTOMER_REQUEST', 'Customer Request'),
        ('OTHER', 'Other'),
    ], default='CUSTOMER_REQUEST')
    reason_details = models.TextField(blank=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2)
    refund_method = models.CharField(max_length=50, choices=[
        ('CASH', 'Cash'),
        ('CARD', 'Card'),
        ('UPI', 'UPI'),
        ('CREDIT_NOTE', 'Credit Note'),
        ('EXCHANGE', 'Exchange'),
    ], default='CASH')
    status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('PROCESSED', 'Processed'),
        ('CANCELLED', 'Cancelled'),
    ], default='PENDING')
    processed_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, related_name='pharmacy_returns_processed')
    processed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-return_date']
    
    def __str__(self):
        return f"Return {self.return_number} - {self.sale.invoice_number}"

class SaleReturnItem(models.Model):
    """Individual items in a return"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='pharmacy_return_items')
    sale_return = models.ForeignKey(SaleReturn, on_delete=models.CASCADE, related_name='items')
    sale_item = models.ForeignKey(SaleItem, on_delete=models.CASCADE)
    medicine_batch = models.ForeignKey(MedicineBatch, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.medicine_batch.medicine.name} - {self.quantity}"

class LoyaltyReward(models.Model):
    """Rewards that customers can redeem with loyalty points"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='pharmacy_loyalty_rewards')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    points_required = models.IntegerField(help_text="Points needed to redeem this reward")
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Discount percentage if applicable")
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Fixed discount amount if applicable")
    reward_type = models.CharField(max_length=50, choices=[
        ('DISCOUNT', 'Discount'),
        ('FREE_ITEM', 'Free Item'),
        ('CASHBACK', 'Cashback'),
        ('OTHER', 'Other'),
    ], default='DISCOUNT')
    is_active = models.BooleanField(default=True)
    valid_from = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['points_required']
    
    def __str__(self):
        return f"{self.name} - {self.points_required} points"

class LoyaltyTransaction(models.Model):
    """Individual loyalty point transactions (earned/spent)"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='pharmacy_loyalty_transactions')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='loyalty_transactions')
    transaction_type = models.CharField(max_length=20, choices=[
        ('EARNED', 'Points Earned'),
        ('REDEEMED', 'Points Redeemed'),
        ('EXPIRED', 'Points Expired'),
        ('ADJUSTED', 'Points Adjusted'),
    ])
    points = models.IntegerField(help_text="Positive for earned, negative for redeemed")
    sale = models.ForeignKey(Sale, on_delete=models.SET_NULL, null=True, blank=True, related_name='loyalty_transactions')
    reward = models.ForeignKey(LoyaltyReward, on_delete=models.SET_NULL, null=True, blank=True, related_name='redemptions')
    description = models.TextField(blank=True)
    expiry_date = models.DateField(null=True, blank=True, help_text="Date when earned points expire (if applicable)")
    transaction_date = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-transaction_date']
    
    def __str__(self):
        return f"{self.customer.name} - {self.transaction_type} - {self.points} points" 