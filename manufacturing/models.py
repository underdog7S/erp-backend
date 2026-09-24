from django.db import models
from api.models.user import Tenant, UserProfile


def _generate_number(prefix):
    import uuid
    from datetime import datetime
    year = datetime.now().year
    month_day = datetime.now().strftime('%m%d')
    unique_part = uuid.uuid4().hex[:4].upper()
    return f"{prefix}-{year}-{month_day}-{unique_part}"


UNIT_OF_MEASURE_CHOICES = [
    ('PCS', 'Pieces'),
    ('KG', 'Kilograms'),
    ('GM', 'Grams'),
    ('LTR', 'Liters'),
    ('MTR', 'Meters'),
    ('BOX', 'Box'),
    ('ROLL', 'Roll'),
    ('SHEET', 'Sheet'),
    ('OTHER', 'Other'),
]


class Supplier(models.Model):
    """Raw material suppliers/vendors"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='manufacturing_suppliers')
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    gst_number = models.CharField(max_length=20, blank=True)
    payment_terms = models.CharField(max_length=100, default='Net 30')
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Warehouse(models.Model):
    """Storage locations - raw material stores, finished goods stores, or general"""
    WAREHOUSE_TYPE_CHOICES = [
        ('RAW_MATERIAL', 'Raw Material Store'),
        ('FINISHED_GOODS', 'Finished Goods Store'),
        ('GENERAL', 'General'),
    ]
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='manufacturing_warehouses')
    name = models.CharField(max_length=100)
    warehouse_type = models.CharField(max_length=20, choices=WAREHOUSE_TYPE_CHOICES, default='GENERAL')
    address = models.TextField(blank=True)
    contact_person = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    is_primary = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class RawMaterial(models.Model):
    """Raw materials consumed by production - a separate stock pool from finished goods"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='raw_materials')
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=50, unique=True)
    category = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    unit_of_measure = models.CharField(max_length=20, choices=UNIT_OF_MEASURE_CHOICES, default='PCS')
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Cost per unit of measure")
    reorder_level = models.IntegerField(default=10)
    hsn_code = models.CharField(max_length=8, blank=True, help_text="HSN code printed on GST invoices")
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="GST percentage, e.g. 5, 12, 18. 0 means no tax is calculated")
    max_stock_level = models.IntegerField(default=1000)
    preferred_supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='supplied_materials')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.sku})"

    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = _generate_number('RM')
        super().save(*args, **kwargs)


class RawMaterialInventory(models.Model):
    """Stock levels of a raw material at a specific warehouse"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE, related_name='inventory')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    quantity_on_hand = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    quantity_reserved = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    quantity_available = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['raw_material', 'warehouse', 'tenant']

    def __str__(self):
        return f"{self.raw_material.name} @ {self.warehouse.name}: {self.quantity_available}"

    def save(self, *args, **kwargs):
        self.quantity_available = self.quantity_on_hand - self.quantity_reserved
        super().save(*args, **kwargs)


class FinishedGood(models.Model):
    """Products produced by the factory - the output of a Production Order"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='finished_goods')
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=50, unique=True)
    category = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    unit_of_measure = models.CharField(max_length=20, choices=UNIT_OF_MEASURE_CHOICES, default='PCS')
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Manufacturing cost per unit, from the active BOM")
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    mrp = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reorder_level = models.IntegerField(default=10)
    hsn_code = models.CharField(max_length=8, blank=True, help_text="HSN code printed on GST invoices")
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="GST percentage, e.g. 5, 12, 18. 0 means no tax is calculated")
    price_includes_tax = models.BooleanField(default=True, help_text="Selling price already contains GST (normal for MRP items)")
    max_stock_level = models.IntegerField(default=1000)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.sku})"

    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = _generate_number('FG')
        if not self.mrp:
            self.mrp = self.selling_price
        super().save(*args, **kwargs)


class FinishedGoodInventory(models.Model):
    """Stock levels of a finished good at a specific warehouse"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    finished_good = models.ForeignKey(FinishedGood, on_delete=models.CASCADE, related_name='inventory')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    quantity_on_hand = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    quantity_reserved = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    quantity_available = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['finished_good', 'warehouse', 'tenant']

    def __str__(self):
        return f"{self.finished_good.name} @ {self.warehouse.name}: {self.quantity_available}"

    def save(self, *args, **kwargs):
        self.quantity_available = self.quantity_on_hand - self.quantity_reserved
        super().save(*args, **kwargs)


class BillOfMaterial(models.Model):
    """Recipe of raw materials that make one unit of a finished good.
    Versioned rather than edited in place, so historical Production Orders
    keep pointing at the exact recipe they were actually built from."""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='bills_of_material')
    finished_good = models.ForeignKey(FinishedGood, on_delete=models.CASCADE, related_name='boms')
    name = models.CharField(max_length=200, blank=True)
    version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True, help_text="Only one active BOM per finished good is used for new Production Orders")
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-version']

    def __str__(self):
        return f"BOM for {self.finished_good.name} v{self.version}"

    def estimated_unit_cost(self):
        total = sum((item.quantity_required * item.raw_material.cost_price for item in self.items.all()), start=0)
        return total


class BOMItem(models.Model):
    """One raw material line in a Bill of Materials"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    bom = models.ForeignKey(BillOfMaterial, on_delete=models.CASCADE, related_name='items')
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE)
    quantity_required = models.DecimalField(max_digits=10, decimal_places=4, help_text="Quantity of this raw material needed per 1 unit of finished good")
    notes = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.raw_material.name} x{self.quantity_required}"


class ProductionOrder(models.Model):
    """A work order: consumes raw materials per the BOM, produces finished goods"""
    STATUS_CHOICES = [
        ('PLANNED', 'Planned'),
        ('IN_PROGRESS', 'In Progress'),
        ('QC_PENDING', 'Awaiting Quality Check'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='production_orders')
    order_number = models.CharField(max_length=50, unique=True)
    bom = models.ForeignKey(BillOfMaterial, on_delete=models.PROTECT, related_name='production_orders')
    finished_good = models.ForeignKey(FinishedGood, on_delete=models.CASCADE, related_name='production_orders')
    quantity_to_produce = models.DecimalField(max_digits=10, decimal_places=2)
    quantity_produced = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    raw_material_warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='production_orders_sourced', help_text="Where raw materials are consumed from")
    output_warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='production_orders_output', help_text="Where finished goods are stored on completion")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PLANNED')
    planned_start_date = models.DateField(null=True, blank=True)
    planned_end_date = models.DateField(null=True, blank=True)
    actual_start_date = models.DateTimeField(null=True, blank=True)
    actual_end_date = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='production_orders_created')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"PROD {self.order_number} - {self.finished_good.name}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = _generate_number('PROD')
        super().save(*args, **kwargs)

    def start_production(self):
        """Consumes raw materials per the BOM x quantity_to_produce. Raises
        ValueError if any raw material doesn't have enough stock - the whole
        order should fail rather than partially consume materials."""
        if self.status != 'PLANNED':
            raise ValueError(f"Can only start a PLANNED order (current status: {self.status})")

        bom_items = list(self.bom.items.select_related('raw_material').all())
        shortfalls = []
        inventories = {}
        for item in bom_items:
            needed = item.quantity_required * self.quantity_to_produce
            inv, _ = RawMaterialInventory.objects.get_or_create(
                raw_material=item.raw_material, warehouse=self.raw_material_warehouse, tenant=self.tenant
            )
            if inv.quantity_available < needed:
                shortfalls.append(f"{item.raw_material.name}: need {needed}, have {inv.quantity_available}")
            inventories[item.id] = (inv, needed)

        if shortfalls:
            raise ValueError("Insufficient raw material stock: " + "; ".join(shortfalls))

        from django.utils import timezone
        for item in bom_items:
            inv, needed = inventories[item.id]
            inv.quantity_on_hand -= needed
            inv.save()

        self.status = 'IN_PROGRESS'
        self.actual_start_date = timezone.now()
        self.save()

    def complete_production(self, quantity_produced=None):
        """Adds the produced quantity to finished goods inventory at output_warehouse."""
        if self.status != 'IN_PROGRESS':
            raise ValueError(f"Can only complete an IN_PROGRESS order (current status: {self.status})")

        from decimal import Decimal
        from django.utils import timezone
        # quantity_produced arrives as a string from the request body when
        # passed explicitly - Decimal field arithmetic below needs a Decimal,
        # not a str, or it raises TypeError.
        qty = Decimal(str(quantity_produced)) if quantity_produced is not None else self.quantity_to_produce
        self.quantity_produced = qty

        inv, _ = FinishedGoodInventory.objects.get_or_create(
            finished_good=self.finished_good, warehouse=self.output_warehouse, tenant=self.tenant
        )
        inv.quantity_on_hand += qty
        inv.save()

        self.status = 'COMPLETED'
        self.actual_end_date = timezone.now()
        self.save()


class QualityCheck(models.Model):
    """Pass/fail checkpoint - either on incoming raw materials (via a Goods
    Receipt line) or on a Production Order's output. Exactly one of
    goods_receipt_item / production_order should be set."""
    CHECK_TYPE_CHOICES = [
        ('INCOMING', 'Incoming Raw Material'),
        ('IN_PROCESS', 'In-Process'),
        ('FINAL', 'Final / Finished Good'),
    ]
    RESULT_CHOICES = [
        ('PENDING', 'Pending'),
        ('PASSED', 'Passed'),
        ('FAILED', 'Failed'),
    ]
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='quality_checks')
    check_type = models.CharField(max_length=20, choices=CHECK_TYPE_CHOICES)
    production_order = models.ForeignKey(ProductionOrder, on_delete=models.CASCADE, null=True, blank=True, related_name='quality_checks')
    goods_receipt_item = models.ForeignKey('GoodsReceiptItem', on_delete=models.CASCADE, null=True, blank=True, related_name='quality_checks')
    quantity_checked = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    quantity_passed = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    quantity_failed = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    parameters_checked = models.TextField(blank=True, help_text="What was inspected - dimensions, purity, weight, etc.")
    result = models.CharField(max_length=20, choices=RESULT_CHOICES, default='PENDING')
    checked_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True)
    checked_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-checked_at']

    def __str__(self):
        return f"QC {self.get_check_type_display()} - {self.result}"


class PurchaseOrder(models.Model):
    """Purchase orders for raw materials from suppliers"""
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('ORDERED', 'Ordered'),
        ('PARTIAL_RECEIVED', 'Partially Received'),
        ('RECEIVED', 'Received'),
        ('CANCELLED', 'Cancelled'),
    ]
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='manufacturing_purchase_orders')
    po_number = models.CharField(max_length=50, unique=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='purchase_orders')
    order_date = models.DateField()
    expected_delivery = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='manufacturing_purchase_orders')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"PO {self.po_number} - {self.supplier.name}"

    def save(self, *args, **kwargs):
        if not self.po_number:
            self.po_number = _generate_number('MPO')
        super().save(*args, **kwargs)


class PurchaseOrderItem(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='manufacturing_purchase_order_items')
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    received_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.raw_material.name} x{self.quantity}"

    def save(self, *args, **kwargs):
        if not self.total_cost:
            self.total_cost = self.quantity * self.unit_cost
        super().save(*args, **kwargs)


class GoodsReceipt(models.Model):
    """Receiving raw materials against a Purchase Order"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='manufacturing_goods_receipts')
    gr_number = models.CharField(max_length=50, unique=True)
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='goods_receipts')
    receipt_date = models.DateField()
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    received_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='manufacturing_goods_receipts_received')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"GR {self.gr_number} - {self.purchase_order.po_number}"

    def save(self, *args, **kwargs):
        if not self.gr_number:
            self.gr_number = _generate_number('MGR')
        super().save(*args, **kwargs)


class GoodsReceiptItem(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='manufacturing_goods_receipt_items')
    goods_receipt = models.ForeignKey(GoodsReceipt, on_delete=models.CASCADE, related_name='items')
    purchase_order_item = models.ForeignKey(PurchaseOrderItem, on_delete=models.CASCADE)
    quantity_received = models.DecimalField(max_digits=10, decimal_places=2)
    quality_status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pending'),
        ('PASSED', 'Passed'),
        ('FAILED', 'Failed'),
    ], default='PENDING')

    def __str__(self):
        return f"{self.purchase_order_item.raw_material.name} x{self.quantity_received}"


class Customer(models.Model):
    """Buyers of finished goods - wholesale-friendly customer types"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='manufacturing_customers')
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    customer_type = models.CharField(max_length=20, choices=[
        ('RETAIL', 'Retail'),
        ('WHOLESALE', 'Wholesale'),
        ('DISTRIBUTOR', 'Distributor'),
    ], default='WHOLESALE')
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_terms = models.CharField(max_length=100, default='Net 30')
    gst_number = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.customer_type})"


class SalesOrder(models.Model):
    """Selling finished goods to customers"""
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('CONFIRMED', 'Confirmed'),
        ('DISPATCHED', 'Dispatched'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
    ]
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='manufacturing_sales_orders')
    so_number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='sales_orders')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, help_text="Finished goods store to dispatch from")
    order_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('PARTIAL', 'Partial'),
    ], default='PENDING')
    created_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='manufacturing_sales_orders')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"SO {self.so_number} - {self.customer.name}"

    def save(self, *args, **kwargs):
        if not self.so_number:
            self.so_number = _generate_number('MSO')
        super().save(*args, **kwargs)


class SalesOrderItem(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name='items')
    finished_good = models.ForeignKey(FinishedGood, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.finished_good.name} x{self.quantity}"

    def save(self, *args, **kwargs):
        if not self.total_price:
            self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)
