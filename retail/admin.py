from django.contrib import admin
from .models import (
    ProductCategory, Supplier, Product, Warehouse, Inventory, Customer,
    PurchaseOrder, PurchaseOrderItem, GoodsReceipt, GoodsReceiptItem,
    Sale, SaleItem, StockTransfer, StockTransferItem, StockAdjustment,
    StockAdjustmentItem, StaffAttendance
)

@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent_category', 'tenant')
    list_filter = ('parent_category', 'tenant')
    search_fields = ('name',)

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'phone', 'email', 'credit_limit', 'tenant')
    list_filter = ('tenant',)
    search_fields = ('name', 'contact_person', 'phone')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'brand', 'cost_price', 'selling_price', 'mrp', 'is_active', 'tenant')
    list_filter = ('category', 'brand', 'unit_of_measure', 'is_active', 'tenant')
    search_fields = ('name', 'sku', 'brand')

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'phone', 'is_primary', 'tenant')
    list_filter = ('is_primary', 'tenant')
    search_fields = ('name', 'contact_person')

@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ('product', 'warehouse', 'quantity_on_hand', 'quantity_reserved', 'quantity_available', 'last_updated', 'tenant')
    list_filter = ('warehouse', 'tenant')
    search_fields = ('product__name', 'product__sku')

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email', 'customer_type', 'credit_limit', 'tenant')
    list_filter = ('customer_type', 'tenant')
    search_fields = ('name', 'phone', 'email')

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('po_number', 'supplier', 'order_date', 'status', 'total_amount', 'tenant')
    list_filter = ('status', 'order_date', 'tenant')
    search_fields = ('po_number', 'supplier__name')

@admin.register(PurchaseOrderItem)
class PurchaseOrderItemAdmin(admin.ModelAdmin):
    list_display = ('purchase_order', 'product', 'quantity', 'unit_cost', 'total_cost', 'received_quantity', 'tenant')
    list_filter = ('tenant',)
    search_fields = ('product__name', 'purchase_order__po_number')

@admin.register(GoodsReceipt)
class GoodsReceiptAdmin(admin.ModelAdmin):
    list_display = ('gr_number', 'purchase_order', 'receipt_date', 'warehouse', 'received_by', 'tenant')
    list_filter = ('receipt_date', 'warehouse', 'tenant')
    search_fields = ('gr_number', 'purchase_order__po_number')

@admin.register(GoodsReceiptItem)
class GoodsReceiptItemAdmin(admin.ModelAdmin):
    list_display = ('goods_receipt', 'purchase_order_item', 'quantity_received', 'quality_check', 'tenant')
    list_filter = ('quality_check', 'tenant')
    search_fields = ('purchase_order_item__product__name', 'goods_receipt__gr_number')

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'customer', 'sale_date', 'warehouse', 'total_amount', 'payment_status', 'tenant')
    list_filter = ('payment_status', 'payment_method', 'sale_date', 'warehouse', 'tenant')
    search_fields = ('invoice_number', 'customer__name')

@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = ('sale', 'product', 'quantity', 'unit_price', 'total_price', 'tenant')
    list_filter = ('tenant',)
    search_fields = ('product__name', 'sale__invoice_number')

@admin.register(StockTransfer)
class StockTransferAdmin(admin.ModelAdmin):
    list_display = ('transfer_number', 'from_warehouse', 'to_warehouse', 'transfer_date', 'status', 'transferred_by', 'tenant')
    list_filter = ('status', 'transfer_date', 'tenant')
    search_fields = ('transfer_number', 'from_warehouse__name', 'to_warehouse__name')

@admin.register(StockTransferItem)
class StockTransferItemAdmin(admin.ModelAdmin):
    list_display = ('stock_transfer', 'product', 'quantity', 'tenant')
    list_filter = ('tenant',)
    search_fields = ('product__name', 'stock_transfer__transfer_number')

@admin.register(StockAdjustment)
class StockAdjustmentAdmin(admin.ModelAdmin):
    list_display = ('adjustment_number', 'warehouse', 'adjustment_type', 'adjustment_date', 'adjusted_by', 'tenant')
    list_filter = ('adjustment_type', 'adjustment_date', 'warehouse', 'tenant')
    search_fields = ('adjustment_number', 'reason')

@admin.register(StockAdjustmentItem)
class StockAdjustmentItemAdmin(admin.ModelAdmin):
    list_display = ('stock_adjustment', 'product', 'quantity', 'tenant')
    list_filter = ('tenant',)
    search_fields = ('product__name', 'stock_adjustment__adjustment_number')

@admin.register(StaffAttendance)
class StaffAttendanceAdmin(admin.ModelAdmin):
    list_display = ('staff', 'date', 'check_in_time', 'check_out_time', 'tenant')
    list_filter = ('date', 'tenant')
    search_fields = ('staff__user__username', 'staff__user__first_name') 