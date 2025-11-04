from django.db import models
from api.models.user import Tenant, UserProfile

class ProductCategory(models.Model):
    """Product categories for organizing inventory"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    parent_category = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')
    
    def __str__(self):
        return self.name

class Supplier(models.Model):
    """Product suppliers/vendors"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='retail_suppliers')
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    address = models.TextField()
    gst_number = models.CharField(max_length=20, blank=True)
    payment_terms = models.CharField(max_length=100, default='Net 30')
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    def __str__(self):
        return self.name

class Product(models.Model):
    """Products/Items in inventory"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=50, unique=True)
    category = models.ForeignKey(ProductCategory, on_delete=models.SET_NULL, null=True)
    brand = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='retail/products/', blank=True, null=True)
    unit_of_measure = models.CharField(max_length=20, choices=[
        ('PCS', 'Pieces'),
        ('KG', 'Kilograms'),
        ('LTR', 'Liters'),
        ('MTR', 'Meters'),
        ('BOX', 'Box'),
        ('PACK', 'Pack'),
        ('OTHER', 'Other'),
    ], default='PCS')
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    mrp = models.DecimalField(max_digits=10, decimal_places=2)
    reorder_level = models.IntegerField(default=10)
    max_stock_level = models.IntegerField(default=100)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} - {self.sku}"

class Warehouse(models.Model):
    """Warehouse locations"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    address = models.TextField()
    contact_person = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    is_primary = models.BooleanField(default=False)
    
    def __str__(self):
        return self.name

class Inventory(models.Model):
    """Inventory tracking for products"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='inventory')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    quantity_on_hand = models.IntegerField(default=0)
    quantity_reserved = models.IntegerField(default=0)
    quantity_available = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['product', 'warehouse', 'tenant']
    
    def __str__(self):
        return f"{self.product.name} - {self.warehouse.name}: {self.quantity_available}"
    
    def save(self, *args, **kwargs):
        self.quantity_available = self.quantity_on_hand - self.quantity_reserved
        super().save(*args, **kwargs)

class PriceList(models.Model):
    """Price lists for different customer types"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='retail_price_lists')
    name = models.CharField(max_length=100, help_text="Name of the price list (e.g., 'Wholesale Price List', 'Distributor Pricing')")
    customer_type = models.CharField(max_length=20, choices=[
        ('RETAIL', 'Retail'),
        ('WHOLESALE', 'Wholesale'),
        ('DISTRIBUTOR', 'Distributor'),
        ('ALL', 'All Types'),
    ], default='ALL', help_text="Customer type this price list applies to")
    is_default = models.BooleanField(default=False, help_text="Default price list for this customer type")
    is_active = models.BooleanField(default=True)
    valid_from = models.DateField(null=True, blank=True, help_text="Price list valid from date")
    valid_to = models.DateField(null=True, blank=True, help_text="Price list valid until date")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['tenant', 'name']
        ordering = ['-is_default', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_customer_type_display()})"

class PriceListItem(models.Model):
    """Individual product prices in a price list"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    price_list = models.ForeignKey(PriceList, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price for this product in this price list")
    min_quantity = models.IntegerField(default=1, help_text="Minimum quantity for this price to apply")
    max_quantity = models.IntegerField(null=True, blank=True, help_text="Maximum quantity for this price (null for unlimited)")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['price_list', 'product', 'min_quantity']
        ordering = ['product__name', 'min_quantity']
    
    def __str__(self):
        return f"{self.product.name} - ₹{self.price} (Qty: {self.min_quantity}+)"

class Customer(models.Model):
    """Retail customers"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='retail_customers')
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    customer_type = models.CharField(max_length=20, choices=[
        ('RETAIL', 'Retail'),
        ('WHOLESALE', 'Wholesale'),
        ('DISTRIBUTOR', 'Distributor'),
    ], default='RETAIL')
    price_list = models.ForeignKey(PriceList, on_delete=models.SET_NULL, null=True, blank=True, related_name='customers', help_text="Custom price list for this customer (overrides default)")
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_terms = models.CharField(max_length=100, default='Cash')
    gst_number = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} - {self.customer_type}"
    
    def get_price_list(self):
        """Get the effective price list for this customer"""
        if self.price_list and self.price_list.is_active:
            return self.price_list
        # Try to find default price list for customer type
        default_list = PriceList.objects.filter(
            tenant=self.tenant,
            customer_type=self.customer_type,
            is_default=True,
            is_active=True
        ).first()
        if default_list:
            return default_list
        # Try to find any active price list for customer type
        return PriceList.objects.filter(
            tenant=self.tenant,
            customer_type__in=[self.customer_type, 'ALL'],
            is_active=True
        ).first()
    
    def get_product_price(self, product, quantity=1):
        """Get the price for a product based on customer's price list"""
        price_list = self.get_price_list()
        if not price_list:
            # Fallback to product's default selling price
            return product.selling_price
        
        # Find matching price list item
        price_item = PriceListItem.objects.filter(
            price_list=price_list,
            product=product,
            is_active=True,
            min_quantity__lte=quantity
        ).order_by('-min_quantity').first()
        
        if price_item:
            # Check max quantity if specified
            if price_item.max_quantity and quantity > price_item.max_quantity:
                # Try to find next tier
                price_item = PriceListItem.objects.filter(
                    price_list=price_list,
                    product=product,
                    is_active=True,
                    min_quantity__lte=quantity,
                    max_quantity__gte=quantity
                ).order_by('-min_quantity').first()
            
            if price_item:
                return price_item.price
        
        # Fallback to product's default selling price
        return product.selling_price

class PurchaseOrder(models.Model):
    """Purchase orders for inventory"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='retail_purchase_orders')
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    po_number = models.CharField(max_length=50, unique=True)
    order_date = models.DateField()
    expected_delivery = models.DateField()
    status = models.CharField(max_length=20, choices=[
        ('DRAFT', 'Draft'),
        ('ORDERED', 'Ordered'),
        ('PARTIAL_RECEIVED', 'Partially Received'),
        ('RECEIVED', 'Received'),
        ('CANCELLED', 'Cancelled'),
    ], default='DRAFT')
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, related_name='retail_purchase_orders')
    
    def __str__(self):
        return f"PO {self.po_number} - {self.supplier.name}"

class PurchaseOrderItem(models.Model):
    """Items in purchase orders"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2)
    received_quantity = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.product.name} - {self.quantity}"

class GoodsReceipt(models.Model):
    """Goods receipt for received purchase orders"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    gr_number = models.CharField(max_length=50, unique=True)
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE)
    receipt_date = models.DateField()
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    received_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True)
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"GR {self.gr_number} - {self.purchase_order.po_number}"

class GoodsReceiptItem(models.Model):
    """Items in goods receipt"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    goods_receipt = models.ForeignKey(GoodsReceipt, on_delete=models.CASCADE, related_name='items')
    purchase_order_item = models.ForeignKey(PurchaseOrderItem, on_delete=models.CASCADE)
    quantity_received = models.IntegerField()
    quality_check = models.CharField(max_length=20, choices=[
        ('PASSED', 'Passed'),
        ('FAILED', 'Failed'),
        ('PENDING', 'Pending'),
    ], default='PENDING')
    
    def __str__(self):
        return f"{self.purchase_order_item.product.name} - {self.quantity_received}"

class Sale(models.Model):
    """Sales transactions"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='retail_sales')
    invoice_number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    sale_date = models.DateTimeField(auto_now_add=True)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=50, choices=[
        ('CASH', 'Cash'),
        ('CARD', 'Card'),
        ('UPI', 'UPI'),
        ('CHEQUE', 'Cheque'),
        ('CREDIT', 'Credit'),
    ], default='CASH')
    payment_status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('PARTIAL', 'Partial'),
    ], default='PAID')
    sold_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, related_name='retail_sales')
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.customer.name}"

class SaleItem(models.Model):
    """Individual items in a sale"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.product.name} - {self.quantity}"

class StockTransfer(models.Model):
    """Stock transfers between warehouses"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    transfer_number = models.CharField(max_length=50, unique=True)
    from_warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='transfers_from')
    to_warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='transfers_to')
    transfer_date = models.DateField()
    status = models.CharField(max_length=20, choices=[
        ('DRAFT', 'Draft'),
        ('IN_TRANSIT', 'In Transit'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ], default='DRAFT')
    transferred_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True)
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"Transfer {self.transfer_number} - {self.from_warehouse} to {self.to_warehouse}"

class StockTransferItem(models.Model):
    """Items in stock transfers"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    stock_transfer = models.ForeignKey(StockTransfer, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    
    def __str__(self):
        return f"{self.product.name} - {self.quantity}"

class StockAdjustment(models.Model):
    """Stock adjustments for inventory management"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    adjustment_number = models.CharField(max_length=50, unique=True)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    adjustment_type = models.CharField(max_length=20, choices=[
        ('ADD', 'Add'),
        ('REMOVE', 'Remove'),
        ('DAMAGED', 'Damaged'),
        ('THEFT', 'Theft'),
        ('LOSS', 'Loss'),
    ])
    reason = models.TextField()
    adjustment_date = models.DateTimeField(auto_now_add=True)
    adjusted_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True)
    
    def __str__(self):
        return f"Adjustment {self.adjustment_number} - {self.adjustment_type}"

class StockAdjustmentItem(models.Model):
    """Items in stock adjustments"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    stock_adjustment = models.ForeignKey(StockAdjustment, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    
    def __str__(self):
        return f"{self.product.name} - {self.quantity}"

class StaffAttendance(models.Model):
    """Staff attendance for retail employees"""
    staff = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='retail_staff_attendance')
    date = models.DateField()
    check_in_time = models.DateTimeField(null=True, blank=True)
    check_out_time = models.DateTimeField(null=True, blank=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='retail_staff_attendance')

    class Meta:
        unique_together = ('staff', 'date', 'tenant')

    def __str__(self):
        return f"{self.staff} - {self.date}"

class SaleReturn(models.Model):
    """Sales returns for retail products"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='retail_sale_returns')
    return_number = models.CharField(max_length=50, unique=True)
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='returns')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    return_date = models.DateTimeField(auto_now_add=True)
    return_type = models.CharField(max_length=20, choices=[
        ('RETURN', 'Return'),
        ('EXCHANGE', 'Exchange'),
        ('REFUND', 'Refund'),
    ], default='RETURN')
    return_reason = models.CharField(max_length=50, choices=[
        ('CUSTOMER_REQUEST', 'Customer Request'),
        ('DAMAGED', 'Damaged'),
        ('DEFECTIVE', 'Defective'),
        ('WRONG_ITEM', 'Wrong Item'),
        ('OTHER', 'Other'),
    ], default='CUSTOMER_REQUEST')
    reason_details = models.TextField(blank=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    refund_method = models.CharField(max_length=20, choices=[
        ('CASH', 'Cash'),
        ('CARD', 'Card'),
        ('UPI', 'UPI'),
        ('CREDIT_NOTE', 'Credit Note'),
    ], default='CASH')
    status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('PROCESSED', 'Processed'),
        ('CANCELLED', 'Cancelled'),
    ], default='PENDING')
    processed_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_retail_returns')
    processed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-return_date']

    def __str__(self):
        return f"Return {self.return_number} - {self.sale.invoice_number}"

class SaleReturnItem(models.Model):
    """Individual items in a sale return"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    sale_return = models.ForeignKey(SaleReturn, on_delete=models.CASCADE, related_name='items')
    sale_item = models.ForeignKey(SaleItem, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    inventory = models.ForeignKey('Inventory', on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField(blank=True)

    def __str__(self):
        return f"{self.product.name} - {self.quantity} units"

class Quotation(models.Model):
    """Quotations for wholesale customers"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='retail_quotations')
    quotation_number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='quotations')
    quotation_date = models.DateField(auto_now_add=True)
    valid_until = models.DateField(help_text="Quotation validity date")
    status = models.CharField(max_length=20, choices=[
        ('DRAFT', 'Draft'),
        ('SENT', 'Sent'),
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
        ('EXPIRED', 'Expired'),
        ('CONVERTED', 'Converted to Sale'),
    ], default='DRAFT')
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Discount percentage if applicable")
    notes = models.TextField(blank=True, help_text="Terms and conditions, delivery terms, etc.")
    created_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, related_name='retail_quotations')
    converted_to_sale = models.ForeignKey('Sale', on_delete=models.SET_NULL, null=True, blank=True, related_name='quotation_source')
    conversion_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-quotation_date']
    
    def __str__(self):
        return f"Quotation {self.quotation_number} - {self.customer.name}"
    
    def is_expired(self):
        """Check if quotation has expired"""
        from django.utils import timezone
        return self.valid_until < timezone.now().date() and self.status not in ['ACCEPTED', 'CONVERTED', 'REJECTED']
    
    def can_convert_to_sale(self):
        """Check if quotation can be converted to sale"""
        return self.status == 'ACCEPTED'

class QuotationItem(models.Model):
    """Individual items in a quotation"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True, help_text="Product-specific notes or specifications")
    
    def __str__(self):
        return f"{self.product.name} - {self.quantity} units @ ₹{self.unit_price}"
    
    def save(self, *args, **kwargs):
        """Auto-calculate total_price"""
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs) 