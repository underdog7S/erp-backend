from rest_framework import serializers
from django.db import models, transaction
from decimal import Decimal
from api.models.user import Tenant, UserProfile
from api.models.custom_service import CustomServiceRequest
from education.models import Class, Student, FeeStructure, FeePayment, FeeDiscount, Attendance, ReportCard, StaffAttendance as EducationStaffAttendance, Department
from pharmacy.models import (
    MasterMedicine, MedicineCategory, Supplier as PharmacySupplier, Medicine, MedicineBatch, Customer as PharmacyCustomer,
    Prescription, PrescriptionItem, Sale as PharmacySale, SaleItem as PharmacySaleItem, PurchaseOrder as PharmacyPurchaseOrder,
    PurchaseOrderItem as PharmacyPurchaseOrderItem, StockAdjustment as PharmacyStockAdjustment, StaffAttendance as PharmacyStaffAttendance,
    SaleReturn as PharmacySaleReturn, SaleReturnItem as PharmacySaleReturnItem,
    LoyaltyReward as PharmacyLoyaltyReward, LoyaltyTransaction as PharmacyLoyaltyTransaction
)
from retail.models import (
    ProductCategory, Supplier as RetailSupplier, Product, Warehouse, Inventory, Customer as RetailCustomer,
    PurchaseOrder as RetailPurchaseOrder, PurchaseOrderItem as RetailPurchaseOrderItem, GoodsReceipt, GoodsReceiptItem,
    Sale as RetailSale, SaleItem as RetailSaleItem, StockTransfer, StockTransferItem, StockAdjustment as RetailStockAdjustment,
    StockAdjustmentItem, StaffAttendance as RetailStaffAttendance,
    SaleReturn as RetailSaleReturn, SaleReturnItem as RetailSaleReturnItem,
    PriceList as RetailPriceList, PriceListItem as RetailPriceListItem,
    Quotation as RetailQuotation, QuotationItem as RetailQuotationItem
)
from hotel.models import RoomType, Room, Guest, Booking, HousekeepingTask, RoomServiceOrder
from salon.models import ServiceCategory, Service, Stylist, Appointment
from restaurant.models import MenuCategory, MenuItem, Table, Order, OrderItem, ExternalAPIIntegration, MenuSyncLog

# Education Serializers
class ClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = Class
        fields = '__all__'
        read_only_fields = ('tenant',)

class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = '__all__'
        read_only_fields = ('tenant',)

class FeeStructureSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeStructure
        fields = '__all__'
        read_only_fields = ('tenant',)

class FeePaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeePayment
        fields = '__all__'
        read_only_fields = ('tenant',)

class FeeDiscountSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeDiscount
        fields = '__all__'
        read_only_fields = ('tenant',)

class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = '__all__'
        read_only_fields = ('tenant',)

class ReportCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportCard
        fields = '__all__'
        read_only_fields = ('tenant',)

class EducationStaffAttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = EducationStaffAttendance
        fields = '__all__'
        read_only_fields = ('tenant',)

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = '__all__'
        read_only_fields = ('tenant',)

# Pharmacy Serializers
class MedicineCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicineCategory
        fields = ['id', 'name', 'description']
        read_only_fields = ('tenant',)

class PharmacySupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = PharmacySupplier
        fields = ['id', 'name', 'contact_person', 'phone', 'email', 'address', 'gst_number', 'payment_terms']
        read_only_fields = ('tenant',)

class MasterMedicineSerializer(serializers.ModelSerializer):
    class Meta:
        model = MasterMedicine
        fields = '__all__'

class MedicineSerializer(serializers.ModelSerializer):
    # Filled by the list view's annotation, summed over in-stock batches
    total_stock = serializers.IntegerField(read_only=True, default=0)
    nearest_expiry = serializers.DateField(read_only=True, default=None)
    sale_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True, default=None)
    sale_mrp = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True, default=None)
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = Medicine
        fields = ['id', 'name', 'generic_name', 'category', 'manufacturer', 'strength', 'dosage_form', 'prescription_required', 'description', 'side_effects', 'storage_conditions', 'expiry_alert_days', 'barcode', 'category_name', 'hsn_code', 'gst_rate', 'price_includes_tax', 'total_stock', 'nearest_expiry', 'sale_price', 'sale_mrp']
        read_only_fields = ('tenant',)

class MedicineBatchSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(source='medicine.name', read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    
    class Meta:
        model = MedicineBatch
        fields = ['id', 'medicine', 'batch_number', 'supplier', 'manufacturing_date', 'expiry_date', 'cost_price', 'selling_price', 'mrp', 'quantity_received', 'quantity_available', 'location', 'medicine_name', 'supplier_name']
        read_only_fields = ('tenant',)

class PharmacyCustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = PharmacyCustomer
        fields = ['id', 'name', 'phone', 'email', 'address', 'date_of_birth', 'allergies', 'medical_history', 
                 'loyalty_points', 'total_points_earned', 'total_points_redeemed', 'loyalty_enrolled', 'created_at']
        read_only_fields = ('tenant', 'loyalty_points', 'total_points_earned', 'total_points_redeemed')

class PrescriptionItemSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(source='medicine.name', read_only=True)
    
    class Meta:
        model = PrescriptionItem
        fields = ['id', 'prescription', 'medicine', 'dosage', 'frequency', 'duration', 'quantity', 'notes', 'medicine_name']
        read_only_fields = ('tenant',)

class PrescriptionSerializer(serializers.ModelSerializer):
    items = PrescriptionItemSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    
    class Meta:
        model = Prescription
        fields = ['id', 'customer', 'doctor_name', 'prescription_date', 'diagnosis', 'notes', 'created_at', 'items', 'customer_name']
        read_only_fields = ('tenant',)

class PharmacySaleItemSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(source='medicine_batch.medicine.name', read_only=True, allow_null=True)
    
    class Meta:
        model = PharmacySaleItem
        fields = ['id', 'sale', 'medicine_batch', 'quantity', 'unit_price', 'total_price', 'medicine_name', 'hsn_code', 'gst_rate', 'tax_amount']
        read_only_fields = ('tenant',)
    
    def to_representation(self, instance):
        """Custom representation to handle null values safely"""
        data = super().to_representation(instance)
        
        # Handle null medicine_batch
        if instance.medicine_batch is None:
            data['medicine_name'] = None
        else:
            data['medicine_name'] = instance.medicine_batch.medicine.name if instance.medicine_batch and instance.medicine_batch.medicine else None
            
        return data

class PharmacySaleSerializer(serializers.ModelSerializer):
    items = PharmacySaleItemSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True, allow_null=True)
    sold_by_name = serializers.CharField(source='sold_by.user.username', read_only=True, allow_null=True)
    
    class Meta:
        model = PharmacySale
        fields = ['id', 'invoice_number', 'customer', 'prescription', 'sale_date', 'subtotal', 'tax_amount', 'cgst_amount', 'sgst_amount', 'discount_amount', 'total_amount', 'payment_method', 'payment_status', 'sold_by', 'notes', 'items', 'customer_name', 'sold_by_name', 'customer_name_input', 'phone']
        read_only_fields = ('tenant', 'invoice_number', 'subtotal', 'tax_amount', 'cgst_amount', 'sgst_amount', 'discount_amount', 'total_amount', 'sale_date')
    
    # Add fields for customer creation (write-only)
    customer_name_input = serializers.CharField(write_only=True, required=False)
    phone = serializers.CharField(write_only=True, required=False)
    
    def to_representation(self, instance):
        """Custom representation to handle null values safely"""
        data = super().to_representation(instance)
        
        # Handle null customer
        if instance.customer is None:
            data['customer_name'] = None
        else:
            data['customer_name'] = instance.customer.name if instance.customer else None
            
        # Handle null sold_by
        if instance.sold_by is None:
            data['sold_by_name'] = None
        else:
            data['sold_by_name'] = instance.sold_by.user.username if instance.sold_by and instance.sold_by.user else None
            
        return data
    
    @transaction.atomic
    def create(self, validated_data):
        items_data = self.context.get('items', [])

        # Handle customer creation if customer_name is provided
        customer_name = validated_data.pop('customer_name_input', None)
        customer_phone = validated_data.pop('phone', None)

        if customer_name and customer_phone:
            # Get tenant from request
            request = self.context.get('request')
            tenant = request.user.userprofile.tenant if request and request.user and hasattr(request.user, 'userprofile') else None

            # Try to find existing customer or create new one
            from pharmacy.models import Customer as PharmacyCustomer
            customer, created = PharmacyCustomer.objects.get_or_create(
                name=customer_name,
                phone=customer_phone,
                tenant=tenant,
                defaults={
                    'email': '',
                    'address': '',
                }
            )
            validated_data['customer'] = customer
        
        # Set tenant for the sale
        request = self.context.get('request')
        if request and request.user and hasattr(request.user, 'userprofile'):
            validated_data['tenant'] = request.user.userprofile.tenant
        else:
            # Fallback: try to get tenant from validated_data
            tenant = validated_data.get('tenant')
            if not tenant:
                raise serializers.ValidationError("Tenant is required")
        
        # Work out, per line, which batches the stock comes from (earliest expiry first, never
        # expired stock) and how much GST is inside the price. Nothing is written until every line
        # can be filled, so a short-stocked bill fails cleanly instead of half-saving.
        from datetime import date
        from pharmacy.models import Medicine as SaleMedicine, MedicineBatch as SaleBatch
        from api.gst import line_tax, split_cgst_sgst
        sale_tenant = validated_data['tenant']
        subtotal = Decimal('0')
        tax_total = Decimal('0')
        added_tax = Decimal('0')
        allocations = []  # (medicine, batch, qty, unit_price, tax)
        for item_data in items_data:
            name = item_data.get('medicine', '')
            try:
                quantity = int(item_data.get('quantity', 1))
                price_given = item_data.get('price')
                price_override = Decimal(str(price_given)) if price_given not in (None, '') else None
            except (ValueError, ArithmeticError):
                raise serializers.ValidationError('Quantity and price must be numbers.')
            if quantity <= 0:
                raise serializers.ValidationError('Quantity must be above zero.')
            # An exact id (from the billing screen) wins; the name match is kept for older callers.
            if item_data.get('medicine_id'):
                medicine = SaleMedicine.objects.filter(id=item_data['medicine_id'], tenant=sale_tenant).first()
            else:
                medicine = SaleMedicine.objects.filter(name__icontains=name, tenant=sale_tenant).first() if name else None
            if not medicine:
                raise serializers.ValidationError(f'Medicine "{name}" was not found.')
            remaining = quantity
            batches = SaleBatch.objects.select_for_update().filter(
                medicine=medicine, tenant=sale_tenant, quantity_available__gt=0, expiry_date__gte=date.today()
            ).order_by('expiry_date', 'id')
            for batch in batches:
                take = min(batch.quantity_available, remaining)
                # Price comes from the batch unless the cashier gives a lower (discounted) price;
                # a medicine can never be billed above its printed MRP.
                unit_price = price_override if price_override is not None else batch.selling_price
                if unit_price < 0 or unit_price > batch.mrp:
                    raise serializers.ValidationError(
                        f'{medicine.name}: price {unit_price} is above the MRP of {batch.mrp} for batch {batch.batch_number}.')
                _, tax = line_tax(take * unit_price, medicine.gst_rate, medicine.price_includes_tax)
                allocations.append((medicine, batch, take, unit_price, tax))
                subtotal += take * unit_price
                tax_total += tax
                if not medicine.price_includes_tax:
                    added_tax += tax
                remaining -= take
                if remaining == 0:
                    break
            if remaining:
                raise serializers.ValidationError(
                    f'{medicine.name}: only {quantity - remaining} in date and in stock, {quantity} requested.')

        cgst, sgst = split_cgst_sgst(tax_total)
        validated_data.update(
            subtotal=subtotal, tax_amount=tax_total, cgst_amount=cgst, sgst_amount=sgst,
            total_amount=subtotal + added_tax, discount_amount=0)

        # Generate invoice number if not provided
        if 'invoice_number' not in validated_data or not validated_data['invoice_number']:
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            validated_data['invoice_number'] = f"INV{timestamp}"

        sale = super().create(validated_data)
        
        # Create sale items from the batch allocations worked out above
        from pharmacy.models import MedicineBatch, SaleItem as PharmacySaleItem
        for medicine, batch, qty, unit_price, tax in allocations:
            PharmacySaleItem.objects.create(
                sale=sale, medicine_batch=batch, quantity=qty, unit_price=unit_price,
                total_price=qty * unit_price, hsn_code=medicine.hsn_code, gst_rate=medicine.gst_rate,
                tax_amount=tax, tenant=sale.tenant)
            MedicineBatch.objects.filter(pk=batch.pk).update(
                quantity_available=models.F('quantity_available') - qty)

        return sale

class PharmacyPurchaseOrderItemSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(source='medicine.name', read_only=True)
    
    class Meta:
        model = PharmacyPurchaseOrderItem
        fields = ['id', 'purchase_order', 'medicine', 'quantity', 'unit_cost', 'total_cost', 'medicine_name']
        read_only_fields = ('tenant',)

class PharmacyPurchaseOrderSerializer(serializers.ModelSerializer):
    items = PharmacyPurchaseOrderItemSerializer(many=True, read_only=True)
    # Write-only list used when creating an order: [{medicine, quantity, unit_cost}, ...]
    items_input = serializers.ListField(child=serializers.DictField(), write_only=True, required=False)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.user.username', read_only=True)
    
    class Meta:
        model = PharmacyPurchaseOrder
        fields = ['id', 'supplier', 'po_number', 'order_date', 'expected_delivery', 'status', 'total_amount', 'notes', 'created_by', 'items', 'items_input', 'supplier_name', 'created_by_name']
        read_only_fields = ('tenant', 'total_amount', 'po_number', 'created_by')

    def validate_supplier(self, supplier):
        request = self.context.get('request')
        if request and supplier.tenant_id != request.user.userprofile.tenant_id:
            raise serializers.ValidationError('Unknown supplier.')
        return supplier

    def create(self, validated_data):
        from django.db import transaction
        items = validated_data.pop('items_input', [])
        if not items:
            raise serializers.ValidationError({'items_input': 'Add at least one medicine to the order.'})
        tenant = validated_data['tenant']
        with transaction.atomic():
            po = PharmacyPurchaseOrder.objects.create(**validated_data)
            total = Decimal('0')
            for row in items:
                medicine = Medicine.objects.filter(id=row.get('medicine'), tenant=tenant).first()
                try:
                    qty = int(row.get('quantity') or 0)
                    cost = Decimal(str(row.get('unit_cost') or 0))
                except (ValueError, ArithmeticError):
                    raise serializers.ValidationError({'items_input': 'Quantity and unit cost must be numbers.'})
                if not medicine or qty <= 0 or cost < 0:
                    raise serializers.ValidationError({'items_input': 'Each line needs a valid medicine, a quantity above zero and a unit cost.'})
                line = qty * cost
                PharmacyPurchaseOrderItem.objects.create(
                    tenant=tenant, purchase_order=po, medicine=medicine,
                    quantity=qty, unit_cost=cost, total_cost=line)
                total += line
            po.total_amount = total
            po.save(update_fields=['total_amount'])
        return po

class PharmacyStockAdjustmentSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(source='medicine_batch.medicine.name', read_only=True)
    adjusted_by_name = serializers.CharField(source='adjusted_by.user.username', read_only=True)
    
    class Meta:
        model = PharmacyStockAdjustment
        fields = ['id', 'medicine_batch', 'adjustment_type', 'quantity', 'reason', 'adjustment_date', 'adjusted_by', 'medicine_name', 'adjusted_by_name']
        read_only_fields = ('tenant', 'adjustment_date', 'adjusted_by')

class PharmacyStaffAttendanceSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source='staff.user.username', read_only=True)
    
    class Meta:
        model = PharmacyStaffAttendance
        fields = ['id', 'staff', 'date', 'check_in_time', 'check_out_time', 'staff_name']
        read_only_fields = ('tenant', 'check_in_time', 'check_out_time')

class PharmacySaleReturnItemSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(source='medicine_batch.medicine.name', read_only=True, allow_null=True)
    batch_number = serializers.CharField(source='medicine_batch.batch_number', read_only=True, allow_null=True)
    
    class Meta:
        model = PharmacySaleReturnItem
        fields = ['id', 'sale_return', 'sale_item', 'medicine_batch', 'quantity', 'unit_price', 'total_price', 'reason', 'medicine_name', 'batch_number']
        read_only_fields = ('tenant',)

class PharmacySaleReturnSerializer(serializers.ModelSerializer):
    items = PharmacySaleReturnItemSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True, allow_null=True)
    sale_invoice_number = serializers.CharField(source='sale.invoice_number', read_only=True)
    processed_by_name = serializers.CharField(source='processed_by.user.username', read_only=True, allow_null=True)
    
    class Meta:
        model = PharmacySaleReturn
        fields = ['id', 'return_number', 'sale', 'customer', 'return_date', 'return_type', 'return_reason', 'reason_details', 
                 'subtotal', 'refund_amount', 'refund_method', 'status', 'processed_by', 'processed_at', 'notes', 
                 'items', 'customer_name', 'sale_invoice_number', 'processed_by_name']
        read_only_fields = ('tenant', 'return_number', 'return_date', 'processed_at')

class PharmacyLoyaltyRewardSerializer(serializers.ModelSerializer):
    class Meta:
        model = PharmacyLoyaltyReward
        fields = ['id', 'name', 'description', 'points_required', 'discount_percentage', 'discount_amount', 
                 'reward_type', 'is_active', 'valid_from', 'valid_until', 'created_at']
        read_only_fields = ('tenant', 'created_at')

class PharmacyLoyaltyTransactionSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    sale_invoice_number = serializers.CharField(source='sale.invoice_number', read_only=True, allow_null=True)
    reward_name = serializers.CharField(source='reward.name', read_only=True, allow_null=True)
    created_by_name = serializers.CharField(source='created_by.user.username', read_only=True, allow_null=True)
    
    class Meta:
        model = PharmacyLoyaltyTransaction
        fields = ['id', 'customer', 'customer_name', 'transaction_type', 'points', 'sale', 'sale_invoice_number', 
                 'reward', 'reward_name', 'description', 'expiry_date', 'transaction_date', 'created_by', 'created_by_name']
        read_only_fields = ('tenant', 'transaction_date')

# Retail Serializers
class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = '__all__'
        read_only_fields = ('tenant',)

class RetailSupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = RetailSupplier
        fields = '__all__'
        read_only_fields = ('tenant',)

class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = '__all__'
        read_only_fields = ('tenant',)

class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    image_url = serializers.SerializerMethodField()
    # Filled by the list view's annotation: units on hand across all warehouses
    total_stock = serializers.IntegerField(read_only=True, default=0)
    
    class Meta:
        model = Product
        fields = '__all__'
        read_only_fields = ('tenant',)
        extra_kwargs = {'sku': {'required': False, 'allow_blank': True}}  # generated when left blank
    
    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

class InventorySerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    
    class Meta:
        model = Inventory
        fields = '__all__'
        read_only_fields = ('tenant',)

class RetailPriceListItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    
    class Meta:
        model = RetailPriceListItem
        fields = ['id', 'price_list', 'product', 'product_name', 'product_sku', 'price', 'min_quantity', 'max_quantity', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ('tenant', 'created_at', 'updated_at')

class RetailPriceListSerializer(serializers.ModelSerializer):
    items = RetailPriceListItemSerializer(many=True, read_only=True)
    items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = RetailPriceList
        fields = ['id', 'name', 'customer_type', 'is_default', 'is_active', 'valid_from', 'valid_to', 'notes', 'created_at', 'updated_at', 'items', 'items_count']
        read_only_fields = ('tenant', 'created_at', 'updated_at')
    
    def get_items_count(self, obj):
        return obj.items.count()

class RetailCustomerSerializer(serializers.ModelSerializer):
    price_list_name = serializers.CharField(source='price_list.name', read_only=True, allow_null=True)
    
    class Meta:
        model = RetailCustomer
        fields = '__all__'
        read_only_fields = ('tenant',)

class RetailPurchaseOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = RetailPurchaseOrderItem
        fields = '__all__'
        read_only_fields = ('tenant',)

def _parse_lines(rows, tenant, model, key='product', with_cost=False):
    """Validate [{product, quantity, unit_cost?}] rows against this tenant's records."""
    out = []
    for row in rows or []:
        obj = model.objects.filter(id=row.get(key), tenant=tenant).first()
        try:
            qty = int(row.get('quantity') or 0)
            cost = Decimal(str(row.get('unit_cost') or 0)) if with_cost else None
        except (ValueError, ArithmeticError):
            raise serializers.ValidationError({'items_input': 'Quantity and unit cost must be numbers.'})
        if not obj or qty <= 0 or (with_cost and cost < 0):
            raise serializers.ValidationError({'items_input': 'Each line needs a valid product and a quantity above zero.'})
        out.append((obj, qty, cost))
    if not out:
        raise serializers.ValidationError({'items_input': 'Add at least one product.'})
    return out


class RetailPurchaseOrderSerializer(serializers.ModelSerializer):
    items = RetailPurchaseOrderItemSerializer(many=True, read_only=True)
    items_input = serializers.ListField(child=serializers.DictField(), write_only=True, required=False)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.user.username', read_only=True)

    class Meta:
        model = RetailPurchaseOrder
        fields = '__all__'
        read_only_fields = ('tenant', 'po_number', 'subtotal', 'tax_amount', 'total_amount', 'created_by')

    def validate_supplier(self, supplier):
        request = self.context.get('request')
        if request and supplier.tenant_id != request.user.userprofile.tenant_id:
            raise serializers.ValidationError('Unknown supplier.')
        return supplier

    def create(self, validated_data):
        from django.db import transaction
        items = validated_data.pop('items_input', None)
        if items is None:
            return super().create(validated_data)
        tenant = validated_data['tenant']
        lines = _parse_lines(items, tenant, Product, with_cost=True)
        with transaction.atomic():
            po = RetailPurchaseOrder.objects.create(**validated_data)
            total = Decimal('0')
            for product, qty, cost in lines:
                RetailPurchaseOrderItem.objects.create(
                    tenant=tenant, purchase_order=po, product=product, quantity=qty,
                    unit_cost=cost, total_cost=qty * cost)
                total += qty * cost
            po.subtotal = po.total_amount = total
            po.save(update_fields=['subtotal', 'total_amount'])
        return po

class GoodsReceiptItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='purchase_order_item.product.name', read_only=True)
    
    class Meta:
        model = GoodsReceiptItem
        fields = '__all__'
        read_only_fields = ('tenant',)

class GoodsReceiptSerializer(serializers.ModelSerializer):
    items = GoodsReceiptItemSerializer(many=True, read_only=True)
    purchase_order_number = serializers.CharField(source='purchase_order.po_number', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    received_by_name = serializers.CharField(source='received_by.user.username', read_only=True)
    
    class Meta:
        model = GoodsReceipt
        fields = '__all__'
        read_only_fields = ('tenant',)

class RetailSaleItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = RetailSaleItem
        fields = '__all__'
        read_only_fields = ('tenant',)

class RetailSaleSerializer(serializers.ModelSerializer):
    items = RetailSaleItemSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True, allow_null=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True, allow_null=True)
    sold_by_name = serializers.CharField(source='sold_by.user.username', read_only=True, allow_null=True)
    
    class Meta:
        model = RetailSale
        fields = ['id', 'invoice_number', 'customer', 'warehouse', 'sale_date', 'subtotal', 'tax_amount', 'cgst_amount', 'sgst_amount', 'discount_amount', 'total_amount', 'payment_method', 'payment_status', 'sold_by', 'notes', 'items', 'customer_name', 'warehouse_name', 'sold_by_name', 'customer_name_input', 'phone']
        read_only_fields = ('tenant', 'invoice_number', 'subtotal', 'tax_amount', 'cgst_amount', 'sgst_amount', 'discount_amount', 'total_amount', 'sale_date')
    
    # Add fields for customer creation (write-only)
    customer_name_input = serializers.CharField(write_only=True, required=False)
    phone = serializers.CharField(write_only=True, required=False)

    def get_extra_kwargs(self):
        kwargs = super().get_extra_kwargs()
        kwargs['customer'] = {**kwargs.get('customer', {}), 'required': False, 'allow_null': True}
        return kwargs

    def to_representation(self, instance):
        """Custom representation to handle null values safely"""
        data = super().to_representation(instance)

        # Handle null customer
        if instance.customer is None:
            data['customer_name'] = None
        else:
            data['customer_name'] = instance.customer.name if instance.customer else None

        # Handle null warehouse
        if instance.warehouse is None:
            data['warehouse_name'] = None
        else:
            data['warehouse_name'] = instance.warehouse.name if instance.warehouse else None
            
        # Handle null sold_by
        if instance.sold_by is None:
            data['sold_by_name'] = None
        else:
            data['sold_by_name'] = instance.sold_by.user.username if instance.sold_by and instance.sold_by.user else None
            
        return data
    
    @transaction.atomic
    def create(self, validated_data):
        items_data = self.context.get('items', [])

        # Handle customer creation if customer_name is provided
        customer_name = validated_data.pop('customer_name_input', None)
        customer_phone = validated_data.pop('phone', None)

        if customer_name and customer_phone:
            # Get tenant from request
            request = self.context.get('request')
            tenant = request.user.userprofile.tenant if request and request.user and hasattr(request.user, 'userprofile') else None

            # Try to find existing customer or create new one
            from retail.models import Customer as RetailCustomer
            customer, created = RetailCustomer.objects.get_or_create(
                name=customer_name,
                phone=customer_phone,
                tenant=tenant,
                defaults={
                    'email': '',
                    'address': '',
                }
            )
            validated_data['customer'] = customer
        
        # Set tenant for the sale
        request = self.context.get('request')
        if request and request.user and hasattr(request.user, 'userprofile'):
            validated_data['tenant'] = request.user.userprofile.tenant
        else:
            # Fallback: try to get tenant from validated_data
            tenant = validated_data.get('tenant')
            if not tenant:
                raise serializers.ValidationError("Tenant is required")

        # A counter sale without a named customer goes on a shared walk-in record
        if not validated_data.get('customer'):
            from retail.models import Customer as WalkInCustomer
            validated_data['customer'], _ = WalkInCustomer.objects.get_or_create(
                tenant=validated_data['tenant'], name='Walk-in Customer', defaults={'phone': '-', 'email': '', 'address': ''})

        # Resolve each line's product first so GST can be worked out per line
        from retail.models import Product as SaleProduct
        from api.gst import line_tax, split_cgst_sgst
        sale_tenant = validated_data['tenant']
        subtotal = Decimal('0')
        tax_total = Decimal('0')
        added_tax = Decimal('0')
        resolved = []  # (product, qty, unit_price, tax)
        for item_data in items_data:
            name = item_data.get('product', '')
            try:
                quantity = int(item_data.get('quantity', 1))
                price_given = item_data.get('price')
                price_override = Decimal(str(price_given)) if price_given not in (None, '') else None
            except (ValueError, ArithmeticError):
                raise serializers.ValidationError('Quantity and price must be numbers.')
            if quantity <= 0:
                raise serializers.ValidationError('Quantity must be above zero.')
            if item_data.get('product_id'):
                product = SaleProduct.objects.filter(id=item_data['product_id'], tenant=sale_tenant).first()
            else:
                product = SaleProduct.objects.filter(name__icontains=name, tenant=sale_tenant).first() if name else None
            if not product:
                raise serializers.ValidationError(f'Product "{name}" was not found.')
            # Default to the catalogue price; a lower (discounted) price is fine, above MRP is not.
            unit_price = price_override if price_override is not None else product.selling_price
            if unit_price < 0 or unit_price > product.mrp:
                raise serializers.ValidationError(f'{product.name}: price {unit_price} is above the MRP of {product.mrp}.')
            _, tax = line_tax(quantity * unit_price, product.gst_rate, product.price_includes_tax)
            subtotal += quantity * unit_price
            tax_total += tax
            if not product.price_includes_tax:
                added_tax += tax
            resolved.append((product, quantity, unit_price, tax))

        cgst, sgst = split_cgst_sgst(tax_total)
        validated_data.update(
            subtotal=subtotal, tax_amount=tax_total, cgst_amount=cgst, sgst_amount=sgst,
            total_amount=subtotal + added_tax, discount_amount=0)

        # Generate invoice number if not provided
        if 'invoice_number' not in validated_data or not validated_data['invoice_number']:
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            validated_data['invoice_number'] = f"RINV{timestamp}"
        
        sale = super().create(validated_data)

        # Create sale items (with the GST worked out above) and take the stock out
        from retail.models import Inventory, SaleItem as RetailSaleItem
        for product, quantity, unit_price, tax in resolved:
            RetailSaleItem.objects.create(
                sale=sale, product=product, quantity=quantity, unit_price=unit_price,
                total_price=quantity * unit_price, hsn_code=product.hsn_code, gst_rate=product.gst_rate,
                tax_amount=tax, tenant=sale.tenant)

            # Deduct sold quantity from inventory at the sale's warehouse
            if sale.warehouse:
                inventory = Inventory.objects.filter(
                    product=product, warehouse=sale.warehouse, tenant=sale.tenant
                ).first()
                if inventory:
                    inventory.quantity_on_hand = max(0, inventory.quantity_on_hand - quantity)
                    inventory.save()

        return sale

class StockTransferItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = StockTransferItem
        fields = '__all__'
        read_only_fields = ('tenant',)

class StockTransferSerializer(serializers.ModelSerializer):
    items = StockTransferItemSerializer(many=True, read_only=True)
    items_input = serializers.ListField(child=serializers.DictField(), write_only=True, required=False)
    from_warehouse_name = serializers.CharField(source='from_warehouse.name', read_only=True)
    to_warehouse_name = serializers.CharField(source='to_warehouse.name', read_only=True)
    transferred_by_name = serializers.CharField(source='transferred_by.user.username', read_only=True)

    class Meta:
        model = StockTransfer
        fields = '__all__'
        read_only_fields = ('tenant', 'transfer_number', 'transferred_by', 'status')

    def validate(self, attrs):
        request = self.context.get('request')
        if request and self.instance is None:
            tenant_id = request.user.userprofile.tenant_id
            for field in ('from_warehouse', 'to_warehouse'):
                if attrs[field].tenant_id != tenant_id:
                    raise serializers.ValidationError({field: 'Unknown warehouse.'})
            if attrs['from_warehouse'].id == attrs['to_warehouse'].id:
                raise serializers.ValidationError({'to_warehouse': 'Choose a different warehouse to send stock to.'})
        return attrs

    def create(self, validated_data):
        from django.db import transaction
        items = validated_data.pop('items_input', None)
        if items is None:
            return super().create(validated_data)
        tenant = validated_data['tenant']
        lines = _parse_lines(items, tenant, Product)
        with transaction.atomic():
            transfer = StockTransfer.objects.create(**validated_data)
            for product, qty, _cost in lines:
                StockTransferItem.objects.create(tenant=tenant, stock_transfer=transfer, product=product, quantity=qty)
        return transfer

class StockAdjustmentItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = StockAdjustmentItem
        fields = '__all__'
        read_only_fields = ('tenant',)

class RetailStockAdjustmentSerializer(serializers.ModelSerializer):
    items = StockAdjustmentItemSerializer(many=True, read_only=True)
    items_input = serializers.ListField(child=serializers.DictField(), write_only=True, required=False)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    adjusted_by_name = serializers.CharField(source='adjusted_by.user.username', read_only=True)

    class Meta:
        model = RetailStockAdjustment
        fields = '__all__'
        read_only_fields = ('tenant', 'adjustment_number', 'adjusted_by')

    def validate_warehouse(self, warehouse):
        request = self.context.get('request')
        if request and warehouse.tenant_id != request.user.userprofile.tenant_id:
            raise serializers.ValidationError('Unknown warehouse.')
        return warehouse

    def create(self, validated_data):
        from django.db import transaction
        from api.retail_stock import credit_stock, debit_stock
        items = validated_data.pop('items_input', None)
        if items is None:
            return super().create(validated_data)
        tenant = validated_data['tenant']
        lines = _parse_lines(items, tenant, Product)
        adding = validated_data['adjustment_type'] == 'ADD'
        with transaction.atomic():
            adj = RetailStockAdjustment.objects.create(**validated_data)
            for product, qty, _cost in lines:
                StockAdjustmentItem.objects.create(tenant=tenant, stock_adjustment=adj, product=product, quantity=qty)
                (credit_stock if adding else debit_stock)(tenant, product, adj.warehouse, qty)
        return adj

class RetailStaffAttendanceSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source='staff.user.username', read_only=True)
    
    class Meta:
        model = RetailStaffAttendance
        fields = '__all__'
        read_only_fields = ('tenant',)

class RetailSaleReturnItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    inventory_warehouse = serializers.CharField(source='inventory.warehouse.name', read_only=True, allow_null=True)
    
    class Meta:
        model = RetailSaleReturnItem
        fields = ['id', 'sale_return', 'sale_item', 'product', 'product_name', 'inventory', 'inventory_warehouse', 'quantity', 'unit_price', 'total_price', 'reason']
        read_only_fields = ('tenant', 'id', 'total_price')

class RetailSaleReturnSerializer(serializers.ModelSerializer):
    items = RetailSaleReturnItemSerializer(many=True, read_only=True)
    sale_invoice_number = serializers.CharField(source='sale.invoice_number', read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    processed_by_name = serializers.CharField(source='processed_by.user.username', read_only=True, allow_null=True)
    
    class Meta:
        model = RetailSaleReturn
        fields = ['id', 'return_number', 'sale', 'sale_invoice_number', 'customer', 'customer_name', 'return_date', 'return_type', 'return_reason', 'reason_details', 'subtotal', 'refund_amount', 'refund_method', 'status', 'processed_by', 'processed_by_name', 'processed_at', 'notes', 'items']
        read_only_fields = ('tenant', 'return_number', 'return_date', 'processed_at')

class RetailQuotationItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    
    class Meta:
        model = RetailQuotationItem
        fields = ['id', 'quotation', 'product', 'product_name', 'product_sku', 'quantity', 'unit_price', 'total_price', 'notes']
        read_only_fields = ('tenant', 'total_price')

class RetailQuotationSerializer(serializers.ModelSerializer):
    items = RetailQuotationItemSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    customer_type = serializers.CharField(source='customer.customer_type', read_only=True)
    created_by_name = serializers.CharField(source='created_by.user.username', read_only=True, allow_null=True)
    converted_to_sale_invoice = serializers.CharField(source='converted_to_sale.invoice_number', read_only=True, allow_null=True)
    is_expired = serializers.SerializerMethodField()
    can_convert = serializers.SerializerMethodField()
    
    class Meta:
        model = RetailQuotation
        fields = ['id', 'quotation_number', 'customer', 'customer_name', 'customer_type', 'quotation_date', 'valid_until', 
                 'status', 'subtotal', 'tax_amount', 'discount_amount', 'discount_percentage', 'total_amount', 
                 'notes', 'created_by', 'created_by_name', 'converted_to_sale', 'converted_to_sale_invoice', 
                 'conversion_date', 'items', 'is_expired', 'can_convert']
        read_only_fields = ('tenant', 'quotation_number', 'quotation_date', 'conversion_date', 'converted_to_sale')
    
    def get_is_expired(self, obj):
        return obj.is_expired()
    
    def get_can_convert(self, obj):
        return obj.can_convert_to_sale()

# Hotel Serializers
class RoomTypeSerializer(serializers.ModelSerializer):
	class Meta:
		model = RoomType
		fields = '__all__'
		read_only_fields = ('tenant',)

class RoomSerializer(serializers.ModelSerializer):
	room_type_name = serializers.CharField(source='room_type.name', read_only=True)
	class Meta:
		model = Room
		fields = '__all__'
		read_only_fields = ('tenant',)

class GuestSerializer(serializers.ModelSerializer):
	class Meta:
		model = Guest
		fields = '__all__'
		read_only_fields = ('tenant',)

class BookingSerializer(serializers.ModelSerializer):
	room_number = serializers.CharField(source='room.room_number', read_only=True)
	room = RoomSerializer(read_only=True)
	guest = GuestSerializer(read_only=True)
	guest_name = serializers.SerializerMethodField()

	class Meta:
		model = Booking
		fields = '__all__'
		read_only_fields = ('tenant',)

	def get_guest_name(self, obj):
		if obj.guest:
			name = f"{obj.guest.first_name} {obj.guest.last_name}".strip()
			return name
		return ""

	def validate(self, data):
		# `room`/`guest` are declared read_only above for representation, so
		# on write they come through as plain PKs in initial_data - fall back
		# to those, then check for overlapping active bookings on the same
		# room. Without this, the room can be double-booked for the same
		# date range with no error.
		room_id = self.initial_data.get('room') or (self.instance.room_id if self.instance else None)
		check_in = data.get('check_in', self.instance.check_in if self.instance else None)
		check_out = data.get('check_out', self.instance.check_out if self.instance else None)
		if room_id and check_in and check_out:
			if check_out <= check_in:
				raise serializers.ValidationError('Check-out must be after check-in.')
			overlap_qs = Booking.objects.filter(
				room_id=room_id,
				check_in__lt=check_out,
				check_out__gt=check_in,
			).exclude(status__in=['cancelled', 'checked_out'])
			if self.instance:
				overlap_qs = overlap_qs.exclude(pk=self.instance.pk)
			if overlap_qs.exists():
				raise serializers.ValidationError('This room is already booked for the selected dates.')
		return data

class HousekeepingTaskSerializer(serializers.ModelSerializer):
	room_number = serializers.CharField(source='room.room_number', read_only=True)

	class Meta:
		model = HousekeepingTask
		fields = '__all__'
		read_only_fields = ('tenant', 'completed_at')

class RoomServiceOrderSerializer(serializers.ModelSerializer):
	room_number = serializers.CharField(source='room.room_number', read_only=True)

	class Meta:
		model = RoomServiceOrder
		fields = '__all__'
		read_only_fields = ('tenant',)

# Restaurant Serializers
class MenuCategorySerializer(serializers.ModelSerializer):
	class Meta:
		model = MenuCategory
		fields = '__all__'
		read_only_fields = ('tenant',)

class MenuItemSerializer(serializers.ModelSerializer):
	category_name = serializers.CharField(source='category.name', read_only=True)
	class Meta:
		model = MenuItem
		fields = '__all__'
		read_only_fields = ('tenant',)

class TableSerializer(serializers.ModelSerializer):
	class Meta:
		model = Table
		fields = '__all__'
		read_only_fields = ('tenant',)

class OrderItemSerializer(serializers.ModelSerializer):
	menu_item_name = serializers.CharField(source='menu_item.name', read_only=True)
	class Meta:
		model = OrderItem
		fields = '__all__'
		read_only_fields = ('tenant',)

class OrderSerializer(serializers.ModelSerializer):
	items = OrderItemSerializer(many=True, read_only=True)
	table = TableSerializer(read_only=True)
	table_number = serializers.CharField(source='table.number', read_only=True, allow_null=True)
	table_id = serializers.PrimaryKeyRelatedField(queryset=Table.objects.all(), source='table', write_only=True, required=False, allow_null=True)
	
	class Meta:
		model = Order
		fields = '__all__'
		read_only_fields = ('tenant',)
	
	def validate(self, data):
		"""Validate order data, especially for cloud kitchen/delivery orders"""
		order_type = data.get('order_type', 'dine_in')
		request = self.context.get('request')
		table = data.get('table')
		if table and request and table.tenant_id != request.user.userprofile.tenant_id:
			raise serializers.ValidationError({'table_id': 'Unknown table.'})
		
		# For cloud kitchen and delivery orders, customer information is required
		if order_type in ['cloud_kitchen', 'delivery', 'takeaway']:
			if not data.get('customer_name'):
				raise serializers.ValidationError({
					'customer_name': 'Customer name is required for cloud kitchen/delivery orders.'
				})
			if not data.get('customer_phone'):
				raise serializers.ValidationError({
					'customer_phone': 'Customer phone number is required for cloud kitchen/delivery orders.'
				})
			if order_type in ['cloud_kitchen', 'delivery'] and not data.get('delivery_address'):
				raise serializers.ValidationError({
					'delivery_address': 'Delivery address is required for cloud kitchen/delivery orders.'
				})
		
		return data
	
	def create(self, validated_data):
		"""Create order and calculate total_amount from items"""
		items_data = self.context.get('items', [])
		
		# Create the order first
		order = Order.objects.create(**validated_data)
		
		# Create order items and calculate total
		total_amount = Decimal('0.00')
		for item_data in items_data:
			menu_item_id = item_data.get('menu_item_id') or item_data.get('menu_item')
			quantity = int(item_data.get('quantity', 1))
			
			try:
				menu_item = MenuItem.objects.get(id=menu_item_id, tenant=order.tenant)
				price = menu_item.price
				
				OrderItem.objects.create(
					tenant=order.tenant,
					order=order,
					menu_item=menu_item,
					quantity=quantity,
					price=price
				)
				
				total_amount += price * quantity
			except MenuItem.DoesNotExist:
				order.delete()  # Rollback order creation
				raise serializers.ValidationError({
					'items': f"Menu item {menu_item_id} not found or unavailable."
				})
			except (ValueError, KeyError) as e:
				order.delete()  # Rollback order creation
				raise serializers.ValidationError({
					'items': f"Invalid item data: {str(e)}"
				})
		
		# Update order with calculated total
		order.total_amount = total_amount
		order.save()

		# The kitchen display picks the order up from here
		from restaurant.kds import create_kds_ticket
		create_kds_ticket(order)

		return order
	
	def update(self, instance, validated_data):
		"""Update order and recalculate total_amount if items changed"""
		items_data = self.context.get('items')
		
		# Update order fields
		for attr, value in validated_data.items():
			setattr(instance, attr, value)
		
		# If items are provided, recalculate total
		if items_data is not None:
			# Delete existing items
			instance.items.all().delete()
			
			# Create new items and calculate total
			total_amount = Decimal('0.00')
			for item_data in items_data:
				menu_item_id = item_data.get('menu_item_id') or item_data.get('menu_item')
				quantity = int(item_data.get('quantity', 1))
				
				try:
					menu_item = MenuItem.objects.get(id=menu_item_id, tenant=instance.tenant)
					price = menu_item.price
					
					OrderItem.objects.create(
						tenant=instance.tenant,
						order=instance,
						menu_item=menu_item,
						quantity=quantity,
						price=price
					)
					
					total_amount += price * quantity
				except MenuItem.DoesNotExist:
					raise serializers.ValidationError({
						'items': f"Menu item {menu_item_id} not found or unavailable."
					})
			
			instance.total_amount = total_amount
		
		instance.save()
		return instance

class ExternalAPIIntegrationSerializer(serializers.ModelSerializer):
	class Meta:
		model = ExternalAPIIntegration
		fields = '__all__'
		read_only_fields = ('tenant', 'last_synced_at', 'created_at', 'updated_at')

class MenuSyncLogSerializer(serializers.ModelSerializer):
	integration_name = serializers.CharField(source='integration.name', read_only=True)
	class Meta:
		model = MenuSyncLog
		fields = '__all__'
		read_only_fields = ('tenant',)

# Public API Serializers (for customer ordering)
class PublicMenuItemSerializer(serializers.ModelSerializer):
	"""Public serializer for menu items (no sensitive data)"""
	category_name = serializers.CharField(source='category.name', read_only=True)
	class Meta:
		model = MenuItem
		fields = ['id', 'name', 'category', 'category_name', 'price', 'is_available']

class PublicMenuCategorySerializer(serializers.ModelSerializer):
	"""Public serializer for menu categories with items"""
	items = serializers.SerializerMethodField()
	class Meta:
		model = MenuCategory
		fields = ['id', 'name', 'description', 'items']
	
	def get_items(self, obj):
		# Filter only available items
		available_items = obj.items.filter(is_available=True)
		return PublicMenuItemSerializer(available_items, many=True).data

class PublicOrderCreateSerializer(serializers.Serializer):
	"""Serializer for public order creation (cloud kitchen)"""
	customer_name = serializers.CharField(max_length=150, required=True)
	customer_phone = serializers.CharField(max_length=20, required=True)
	customer_email = serializers.EmailField(required=False, allow_blank=True)
	delivery_address = serializers.CharField(required=True)
	order_type = serializers.ChoiceField(choices=['delivery', 'takeaway', 'cloud_kitchen'], default='cloud_kitchen')
	items = serializers.ListField(
		child=serializers.DictField(child=serializers.CharField()),
		required=True
	)
	notes = serializers.CharField(required=False, allow_blank=True)

# Salon Serializers
class ServiceCategorySerializer(serializers.ModelSerializer):
	class Meta:
		model = ServiceCategory
		fields = '__all__'
		read_only_fields = ('tenant',)  # Exclude tenant from validation since it's set in perform_create
	
	def validate(self, data):
		print(f"ServiceCategorySerializer.validate called with data: {data}")
		return data
	
	def create(self, validated_data):
		print(f"ServiceCategorySerializer.create called with validated_data: {validated_data}")
		return super().create(validated_data)

class ServiceSerializer(serializers.ModelSerializer):
	category_name = serializers.CharField(source='category.name', read_only=True)
	image_url = serializers.SerializerMethodField()
	
	class Meta:
		model = Service
		fields = '__all__'
		read_only_fields = ('tenant',)  # Exclude tenant from validation since it's set in perform_create
	
	def get_image_url(self, obj):
		if obj.image:
			request = self.context.get('request')
			if request:
				return request.build_absolute_uri(obj.image.url)
			return obj.image.url
		return None

class StylistSerializer(serializers.ModelSerializer):
	class Meta:
		model = Stylist
		fields = '__all__'
		read_only_fields = ('tenant',)  # Exclude tenant from validation since it's set in perform_create

class AppointmentSerializer(serializers.ModelSerializer):
	service_name = serializers.CharField(source='service.name', read_only=True)
	stylist_name = serializers.SerializerMethodField()
	class Meta:
		model = Appointment
		fields = '__all__'
		read_only_fields = ('tenant',)  # Exclude tenant from validation since it's set in perform_create
		extra_kwargs = {'end_time': {'required': False}, 'price': {'required': False}}

	def get_stylist_name(self, obj):
		return f"{obj.stylist.first_name} {obj.stylist.last_name}".strip()

	def validate(self, data):
		"""Fill in end time and price from the service, and refuse a double-booked stylist."""
		from datetime import timedelta
		request = self.context.get('request')
		service, stylist = data.get('service'), data.get('stylist')
		if request and self.instance is None:
			tenant_id = request.user.userprofile.tenant_id
			for obj, label in ((service, 'service'), (stylist, 'stylist')):
				if obj and obj.tenant_id != tenant_id:
					raise serializers.ValidationError({label: 'Unknown ' + label + '.'})
		start = data.get('start_time')
		if service and start:
			if not data.get('end_time'):
				data['end_time'] = start + timedelta(minutes=service.duration_minutes)
			if data.get('price') is None:
				data['price'] = service.price
		end = data.get('end_time')
		if stylist and start and end:
			if end <= start:
				raise serializers.ValidationError({'end_time': 'The end must be after the start.'})
			clash = Appointment.objects.filter(stylist=stylist, start_time__lt=end, end_time__gt=start).exclude(status='cancelled')
			if self.instance is not None:
				clash = clash.exclude(pk=self.instance.pk)
			if clash.exists():
				raise serializers.ValidationError({'stylist': 'This stylist already has an appointment at that time.'})
		return data

# Alias serializers for backward compatibility
SupplierSerializer = PharmacySupplierSerializer
CustomerSerializer = PharmacyCustomerSerializer
SaleSerializer = PharmacySaleSerializer
SaleItemSerializer = PharmacySaleItemSerializer
PurchaseOrderSerializer = PharmacyPurchaseOrderSerializer
PurchaseOrderItemSerializer = PharmacyPurchaseOrderItemSerializer
StockAdjustmentSerializer = PharmacyStockAdjustmentSerializer
StaffAttendanceSerializer = PharmacyStaffAttendanceSerializer
SaleReturnSerializer = PharmacySaleReturnSerializer
SaleReturnItemSerializer = PharmacySaleReturnItemSerializer

# Notification Serializers
from api.models.notifications import Notification, NotificationPreference, NotificationTemplate, NotificationLog

class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model"""
    time_ago = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id', 'title', 'message', 'notification_type', 'module', 'priority',
            'action_url', 'action_label', 'reference_type', 'reference_id',
            'read', 'read_at', 'icon', 'created_at', 'expires_at',
            'time_ago', 'is_expired'
        ]
        read_only_fields = ['id', 'created_at', 'read_at']
    
    def get_time_ago(self, obj):
        """Human-readable time difference"""
        from django.utils import timezone
        from datetime import timedelta
        delta = timezone.now() - obj.created_at
        if delta < timedelta(minutes=1):
            return "Just now"
        elif delta < timedelta(hours=1):
            minutes = int(delta.total_seconds() / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif delta < timedelta(days=1):
            hours = int(delta.total_seconds() / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif delta < timedelta(days=7):
            days = delta.days
            return f"{days} day{'s' if days != 1 else ''} ago"
        else:
            return obj.created_at.strftime("%b %d, %Y")
    
    def get_is_expired(self, obj):
        """Check if notification is expired"""
        return obj.is_expired()


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for NotificationPreference model"""
    class Meta:
        model = NotificationPreference
        fields = [
            'id', 'email_enabled', 'sms_enabled', 'push_enabled', 'in_app_enabled',
            'module_preferences', 'type_preferences',
            'quiet_hours_start', 'quiet_hours_end',
            'max_emails_per_day', 'max_sms_per_day',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class NotificationTemplateSerializer(serializers.ModelSerializer):
    """Serializer for NotificationTemplate model"""
    class Meta:
        model = NotificationTemplate
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class NotificationLogSerializer(serializers.ModelSerializer):
    """Serializer for NotificationLog model"""
    class Meta:
        model = NotificationLog
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


class NotificationStatsSerializer(serializers.Serializer):
    """Serializer for notification statistics"""
    total = serializers.IntegerField()
    unread = serializers.IntegerField()
    by_type = serializers.DictField()
    by_module = serializers.DictField()
    by_priority = serializers.DictField()
    recent_count = serializers.IntegerField(help_text="Count of notifications from last 24 hours")

class CustomServiceRequestSerializer(serializers.ModelSerializer):
    """Serializer for Custom Service Request model"""
    service_type_display = serializers.CharField(source='get_service_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = CustomServiceRequest
        fields = [
            'id', 'service_type', 'service_type_display', 'name', 'email', 
            'phone', 'company_name', 'description', 'budget_range', 'timeline',
            'status', 'status_display', 'notes', 'submitted_at', 'contacted_at'
        ]
        read_only_fields = ['id', 'status', 'submitted_at', 'contacted_at'] 

from education.models import Assignment, AssignmentSubmission, Grade

class AssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        fields = '__all__'

class AssignmentSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssignmentSubmission
        fields = '__all__'

class GradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Grade
        fields = '__all__'