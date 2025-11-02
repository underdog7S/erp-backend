from rest_framework import serializers
from api.models.user import Tenant, UserProfile
from api.models.custom_service import CustomServiceRequest
from education.models import Class, Student, FeeStructure, FeePayment, FeeDiscount, Attendance, ReportCard, StaffAttendance as EducationStaffAttendance, Department
from pharmacy.models import (
    MedicineCategory, Supplier as PharmacySupplier, Medicine, MedicineBatch, Customer as PharmacyCustomer,
    Prescription, PrescriptionItem, Sale as PharmacySale, SaleItem as PharmacySaleItem, PurchaseOrder as PharmacyPurchaseOrder,
    PurchaseOrderItem as PharmacyPurchaseOrderItem, StockAdjustment as PharmacyStockAdjustment, StaffAttendance as PharmacyStaffAttendance
)
from retail.models import (
    ProductCategory, Supplier as RetailSupplier, Product, Warehouse, Inventory, Customer as RetailCustomer,
    PurchaseOrder as RetailPurchaseOrder, PurchaseOrderItem as RetailPurchaseOrderItem, GoodsReceipt, GoodsReceiptItem,
    Sale as RetailSale, SaleItem as RetailSaleItem, StockTransfer, StockTransferItem, StockAdjustment as RetailStockAdjustment,
    StockAdjustmentItem, StaffAttendance as RetailStaffAttendance
)
from hotel.models import RoomType, Room, Guest, Booking
from salon.models import ServiceCategory, Service, Stylist, Appointment
from restaurant.models import MenuCategory, MenuItem, Table, Order, OrderItem

# Education Serializers
class ClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = Class
        fields = '__all__'

class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = '__all__'

class FeeStructureSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeStructure
        fields = '__all__'

class FeePaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeePayment
        fields = '__all__'

class FeeDiscountSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeDiscount
        fields = '__all__'

class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = '__all__'

class ReportCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportCard
        fields = '__all__'

class EducationStaffAttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = EducationStaffAttendance
        fields = '__all__'

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = '__all__'

# Pharmacy Serializers
class MedicineCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicineCategory
        fields = ['id', 'name', 'description']

class PharmacySupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = PharmacySupplier
        fields = ['id', 'name', 'contact_person', 'phone', 'email', 'address', 'gst_number', 'payment_terms']

class MedicineSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = Medicine
        fields = ['id', 'name', 'generic_name', 'category', 'manufacturer', 'strength', 'dosage_form', 'prescription_required', 'description', 'side_effects', 'storage_conditions', 'expiry_alert_days', 'barcode', 'category_name']

class MedicineBatchSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(source='medicine.name', read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    
    class Meta:
        model = MedicineBatch
        fields = ['id', 'medicine', 'batch_number', 'supplier', 'manufacturing_date', 'expiry_date', 'cost_price', 'selling_price', 'mrp', 'quantity_received', 'quantity_available', 'location', 'medicine_name', 'supplier_name']

class PharmacyCustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = PharmacyCustomer
        fields = ['id', 'name', 'phone', 'email', 'address', 'date_of_birth', 'allergies', 'medical_history', 'created_at']

class PrescriptionItemSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(source='medicine.name', read_only=True)
    
    class Meta:
        model = PrescriptionItem
        fields = ['id', 'prescription', 'medicine', 'dosage', 'frequency', 'duration', 'quantity', 'notes', 'medicine_name']

class PrescriptionSerializer(serializers.ModelSerializer):
    items = PrescriptionItemSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    
    class Meta:
        model = Prescription
        fields = ['id', 'customer', 'doctor_name', 'prescription_date', 'diagnosis', 'notes', 'created_at', 'items', 'customer_name']

class PharmacySaleItemSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(source='medicine_batch.medicine.name', read_only=True, allow_null=True)
    
    class Meta:
        model = PharmacySaleItem
        fields = ['id', 'sale', 'medicine_batch', 'quantity', 'unit_price', 'total_price', 'medicine_name']
    
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
        fields = ['id', 'invoice_number', 'customer', 'prescription', 'sale_date', 'subtotal', 'tax_amount', 'discount_amount', 'total_amount', 'payment_method', 'payment_status', 'sold_by', 'notes', 'items', 'customer_name', 'sold_by_name', 'customer_name_input', 'phone']
        read_only_fields = ['invoice_number', 'subtotal', 'tax_amount', 'discount_amount', 'total_amount', 'sale_date']
    
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
        
        # Calculate totals from items
        subtotal = 0
        for item_data in items_data:
            quantity = item_data.get('quantity', 1)
            price = item_data.get('price', 0)
            subtotal += quantity * price
        
        # Set required fields
        validated_data['subtotal'] = subtotal
        validated_data['total_amount'] = subtotal  # No tax/discount for now
        validated_data['tax_amount'] = 0
        validated_data['discount_amount'] = 0
        
        # Generate invoice number if not provided
        if 'invoice_number' not in validated_data or not validated_data['invoice_number']:
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            validated_data['invoice_number'] = f"INV{timestamp}"
        
        sale = super().create(validated_data)
        
        # Create sale items
        for item_data in items_data:
            # Find the medicine batch for this medicine
            medicine_name = item_data.get('medicine', '')
            if medicine_name:
                try:
                    # Find medicine by name (use first() to avoid multiple results)
                    from pharmacy.models import Medicine
                    medicine = Medicine.objects.filter(name__icontains=medicine_name).first()
                    if medicine:
                        # Get the first available batch for this medicine
                        from pharmacy.models import MedicineBatch
                        medicine_batch = MedicineBatch.objects.filter(
                            medicine=medicine,
                            quantity_available__gt=0
                        ).first()
                    
                    if medicine_batch:
                        from pharmacy.models import SaleItem as PharmacySaleItem
                        PharmacySaleItem.objects.create(
                            sale=sale,
                            medicine_batch=medicine_batch,
                            quantity=item_data.get('quantity', 1),
                            unit_price=item_data.get('price', 0),
                            total_price=item_data.get('quantity', 1) * item_data.get('price', 0),
                            tenant=sale.tenant
                        )
                except Medicine.DoesNotExist:
                    # If medicine not found, create a placeholder item
                    from pharmacy.models import SaleItem as PharmacySaleItem
                    PharmacySaleItem.objects.create(
                        sale=sale,
                        medicine_batch=None,
                        quantity=item_data.get('quantity', 1),
                        unit_price=item_data.get('price', 0),
                        total_price=item_data.get('quantity', 1) * item_data.get('price', 0),
                        tenant=sale.tenant
                    )
        
        return sale

class PharmacyPurchaseOrderItemSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(source='medicine.name', read_only=True)
    
    class Meta:
        model = PharmacyPurchaseOrderItem
        fields = ['id', 'purchase_order', 'medicine', 'quantity', 'unit_cost', 'total_cost', 'medicine_name']

class PharmacyPurchaseOrderSerializer(serializers.ModelSerializer):
    items = PharmacyPurchaseOrderItemSerializer(many=True, read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.user.username', read_only=True)
    
    class Meta:
        model = PharmacyPurchaseOrder
        fields = ['id', 'supplier', 'po_number', 'order_date', 'expected_delivery', 'status', 'total_amount', 'notes', 'created_by', 'items', 'supplier_name', 'created_by_name']

class PharmacyStockAdjustmentSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(source='medicine_batch.medicine.name', read_only=True)
    adjusted_by_name = serializers.CharField(source='adjusted_by.user.username', read_only=True)
    
    class Meta:
        model = PharmacyStockAdjustment
        fields = ['id', 'medicine_batch', 'adjustment_type', 'quantity', 'reason', 'adjustment_date', 'adjusted_by', 'medicine_name', 'adjusted_by_name']
        read_only_fields = ['adjustment_date', 'adjusted_by']

class PharmacyStaffAttendanceSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source='staff.user.username', read_only=True)
    
    class Meta:
        model = PharmacyStaffAttendance
        fields = ['id', 'staff', 'date', 'check_in_time', 'check_out_time', 'staff_name']
        read_only_fields = ['check_in_time', 'check_out_time']

# Retail Serializers
class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = '__all__'

class RetailSupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = RetailSupplier
        fields = '__all__'

class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = '__all__'
    
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

class RetailCustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = RetailCustomer
        fields = '__all__'

class RetailPurchaseOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = RetailPurchaseOrderItem
        fields = '__all__'

class RetailPurchaseOrderSerializer(serializers.ModelSerializer):
    items = RetailPurchaseOrderItemSerializer(many=True, read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.user.username', read_only=True)
    
    class Meta:
        model = RetailPurchaseOrder
        fields = '__all__'

class GoodsReceiptItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='purchase_order_item.product.name', read_only=True)
    
    class Meta:
        model = GoodsReceiptItem
        fields = '__all__'

class GoodsReceiptSerializer(serializers.ModelSerializer):
    items = GoodsReceiptItemSerializer(many=True, read_only=True)
    purchase_order_number = serializers.CharField(source='purchase_order.po_number', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    received_by_name = serializers.CharField(source='received_by.user.username', read_only=True)
    
    class Meta:
        model = GoodsReceipt
        fields = '__all__'

class RetailSaleItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = RetailSaleItem
        fields = '__all__'

class RetailSaleSerializer(serializers.ModelSerializer):
    items = RetailSaleItemSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True, allow_null=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True, allow_null=True)
    sold_by_name = serializers.CharField(source='sold_by.user.username', read_only=True, allow_null=True)
    
    class Meta:
        model = RetailSale
        fields = ['id', 'invoice_number', 'customer', 'warehouse', 'sale_date', 'subtotal', 'tax_amount', 'discount_amount', 'total_amount', 'payment_method', 'payment_status', 'sold_by', 'notes', 'items', 'customer_name', 'warehouse_name', 'sold_by_name', 'customer_name_input', 'phone']
        read_only_fields = ['invoice_number', 'subtotal', 'tax_amount', 'discount_amount', 'total_amount', 'sale_date']
    
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
        
        # Calculate totals from items
        subtotal = 0
        for item_data in items_data:
            quantity = item_data.get('quantity', 1)
            price = item_data.get('price', 0)
            subtotal += quantity * price
        
        # Set required fields
        validated_data['subtotal'] = subtotal
        validated_data['total_amount'] = subtotal  # No tax/discount for now
        validated_data['tax_amount'] = 0
        validated_data['discount_amount'] = 0
        
        # Generate invoice number if not provided
        if 'invoice_number' not in validated_data or not validated_data['invoice_number']:
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            validated_data['invoice_number'] = f"RINV{timestamp}"
        
        sale = super().create(validated_data)
        
        # Create sale items
        for item_data in items_data:
            # Find the product for this item
            product_name = item_data.get('product', '')
            if product_name:
                try:
                    # Find product by name (use first() to avoid multiple results)
                    from retail.models import Product
                    product = Product.objects.filter(name__icontains=product_name).first()
                    if product:
                        from retail.models import SaleItem as RetailSaleItem
                        RetailSaleItem.objects.create(
                            sale=sale,
                            product=product,
                            quantity=item_data.get('quantity', 1),
                            unit_price=item_data.get('price', 0),
                            total_price=item_data.get('quantity', 1) * item_data.get('price', 0),
                            tenant=sale.tenant
                        )
                except Product.DoesNotExist:
                    # If product not found, create a placeholder item
                    from retail.models import SaleItem as RetailSaleItem
                    RetailSaleItem.objects.create(
                        sale=sale,
                        product=None,
                        quantity=item_data.get('quantity', 1),
                        unit_price=item_data.get('price', 0),
                        total_price=item_data.get('quantity', 1) * item_data.get('price', 0),
                        tenant=sale.tenant
                    )
        
        return sale

class StockTransferItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = StockTransferItem
        fields = '__all__'

class StockTransferSerializer(serializers.ModelSerializer):
    items = StockTransferItemSerializer(many=True, read_only=True)
    from_warehouse_name = serializers.CharField(source='from_warehouse.name', read_only=True)
    to_warehouse_name = serializers.CharField(source='to_warehouse.name', read_only=True)
    transferred_by_name = serializers.CharField(source='transferred_by.user.username', read_only=True)
    
    class Meta:
        model = StockTransfer
        fields = '__all__'

class StockAdjustmentItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = StockAdjustmentItem
        fields = '__all__'

class RetailStockAdjustmentSerializer(serializers.ModelSerializer):
    items = StockAdjustmentItemSerializer(many=True, read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    adjusted_by_name = serializers.CharField(source='adjusted_by.user.username', read_only=True)
    
    class Meta:
        model = RetailStockAdjustment
        fields = '__all__'

class RetailStaffAttendanceSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source='staff.user.username', read_only=True)
    
    class Meta:
        model = RetailStaffAttendance
        fields = '__all__'

# Hotel Serializers
class RoomTypeSerializer(serializers.ModelSerializer):
	class Meta:
		model = RoomType
		fields = '__all__'

class RoomSerializer(serializers.ModelSerializer):
	room_type_name = serializers.CharField(source='room_type.name', read_only=True)
	class Meta:
		model = Room
		fields = '__all__'

class GuestSerializer(serializers.ModelSerializer):
	class Meta:
		model = Guest
		fields = '__all__'

class BookingSerializer(serializers.ModelSerializer):
	room_number = serializers.CharField(source='room.room_number', read_only=True)
	guest_name = serializers.SerializerMethodField()

	class Meta:
		model = Booking
		fields = '__all__'

	def get_guest_name(self, obj):
		name = f"{obj.guest.first_name} {obj.guest.last_name}".strip()
		return name

# Restaurant Serializers
class MenuCategorySerializer(serializers.ModelSerializer):
	class Meta:
		model = MenuCategory
		fields = '__all__'

class MenuItemSerializer(serializers.ModelSerializer):
	category_name = serializers.CharField(source='category.name', read_only=True)
	class Meta:
		model = MenuItem
		fields = '__all__'

class TableSerializer(serializers.ModelSerializer):
	class Meta:
		model = Table
		fields = '__all__'

class OrderItemSerializer(serializers.ModelSerializer):
	menu_item_name = serializers.CharField(source='menu_item.name', read_only=True)
	class Meta:
		model = OrderItem
		fields = '__all__'

class OrderSerializer(serializers.ModelSerializer):
	items = OrderItemSerializer(many=True, read_only=True)
	table_number = serializers.CharField(source='table.number', read_only=True, allow_null=True)
	class Meta:
		model = Order
		fields = '__all__'

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

	def get_stylist_name(self, obj):
		return f"{obj.stylist.first_name} {obj.stylist.last_name}".strip()

# Alias serializers for backward compatibility
SupplierSerializer = PharmacySupplierSerializer
CustomerSerializer = PharmacyCustomerSerializer
SaleSerializer = PharmacySaleSerializer
SaleItemSerializer = PharmacySaleItemSerializer
PurchaseOrderSerializer = PharmacyPurchaseOrderSerializer
PurchaseOrderItemSerializer = PharmacyPurchaseOrderItemSerializer
StockAdjustmentSerializer = PharmacyStockAdjustmentSerializer
StaffAttendanceSerializer = PharmacyStaffAttendanceSerializer

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