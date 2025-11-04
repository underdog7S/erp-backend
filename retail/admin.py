from django.contrib import admin
from .models import (
    ProductCategory, Supplier, Product, Warehouse, Inventory, Customer,
    PurchaseOrder, PurchaseOrderItem, GoodsReceipt, GoodsReceiptItem,
    Sale, SaleItem, StockTransfer, StockTransferItem, StockAdjustment,
    StockAdjustmentItem, StaffAttendance, SaleReturn, SaleReturnItem,
    PriceList, PriceListItem, Quotation, QuotationItem
)
from api.admin_site import secure_admin_site

class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent_category', 'tenant')
    list_filter = ('parent_category', 'tenant')
    search_fields = ('name',)

class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'phone', 'email', 'credit_limit', 'tenant')
    list_filter = ('tenant',)
    search_fields = ('name', 'contact_person', 'phone')

class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'brand', 'cost_price', 'selling_price', 'mrp', 'is_active', 'tenant')
    list_filter = ('category', 'brand', 'unit_of_measure', 'is_active', 'tenant')
    search_fields = ('name', 'sku', 'brand')

class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'phone', 'is_primary', 'tenant')
    list_filter = ('is_primary', 'tenant')
    search_fields = ('name', 'contact_person')

class InventoryAdmin(admin.ModelAdmin):
    list_display = ('product', 'warehouse', 'quantity_on_hand', 'quantity_reserved', 'quantity_available', 'last_updated', 'tenant')
    list_filter = ('warehouse', 'tenant')
    search_fields = ('product__name', 'product__sku')

class PriceListItemInline(admin.TabularInline):
    model = PriceListItem
    extra = 1
    fields = ('product', 'price', 'min_quantity', 'max_quantity', 'is_active')
    autocomplete_fields = ['product']

class PriceListAdmin(admin.ModelAdmin):
    list_display = ('name', 'customer_type', 'is_default', 'is_active', 'valid_from', 'valid_to', 'tenant')
    list_filter = ('customer_type', 'is_default', 'is_active', 'tenant')
    search_fields = ('name',)
    inlines = [PriceListItemInline]
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'customer_type', 'tenant')
        }),
        ('Status', {
            'fields': ('is_default', 'is_active', 'valid_from', 'valid_to')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
    )

class PriceListItemAdmin(admin.ModelAdmin):
    list_display = ('price_list', 'product', 'price', 'min_quantity', 'max_quantity', 'is_active', 'tenant')
    list_filter = ('price_list', 'is_active', 'tenant')
    search_fields = ('product__name', 'product__sku', 'price_list__name')
    autocomplete_fields = ['product', 'price_list']

class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email', 'customer_type', 'price_list', 'credit_limit', 'tenant')
    list_filter = ('customer_type', 'price_list', 'tenant')
    search_fields = ('name', 'phone', 'email')
    autocomplete_fields = ['price_list']

class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('po_number', 'supplier', 'order_date', 'status', 'total_amount', 'tenant')
    list_filter = ('status', 'order_date', 'tenant')
    search_fields = ('po_number', 'supplier__name')

class PurchaseOrderItemAdmin(admin.ModelAdmin):
    list_display = ('purchase_order', 'product', 'quantity', 'unit_cost', 'total_cost', 'received_quantity', 'tenant')
    list_filter = ('tenant',)
    search_fields = ('product__name', 'purchase_order__po_number')

class GoodsReceiptAdmin(admin.ModelAdmin):
    list_display = ('gr_number', 'purchase_order', 'receipt_date', 'warehouse', 'received_by', 'tenant')
    list_filter = ('receipt_date', 'warehouse', 'tenant')
    search_fields = ('gr_number', 'purchase_order__po_number')

class GoodsReceiptItemAdmin(admin.ModelAdmin):
    list_display = ('goods_receipt', 'purchase_order_item', 'quantity_received', 'quality_check', 'tenant')
    list_filter = ('quality_check', 'tenant')
    search_fields = ('purchase_order_item__product__name', 'goods_receipt__gr_number')

class SaleAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'customer', 'sale_date', 'warehouse', 'total_amount', 'payment_status', 'tenant')
    list_filter = ('payment_status', 'payment_method', 'sale_date', 'warehouse', 'tenant')
    search_fields = ('invoice_number', 'customer__name')

class SaleItemAdmin(admin.ModelAdmin):
    list_display = ('sale', 'product', 'quantity', 'unit_price', 'total_price', 'tenant')
    list_filter = ('tenant',)
    search_fields = ('product__name', 'sale__invoice_number')

class StockTransferAdmin(admin.ModelAdmin):
    list_display = ('transfer_number', 'from_warehouse', 'to_warehouse', 'transfer_date', 'status', 'transferred_by', 'tenant')
    list_filter = ('status', 'transfer_date', 'tenant')
    search_fields = ('transfer_number', 'from_warehouse__name', 'to_warehouse__name')

class StockTransferItemAdmin(admin.ModelAdmin):
    list_display = ('stock_transfer', 'product', 'quantity', 'tenant')
    list_filter = ('tenant',)
    search_fields = ('product__name', 'stock_transfer__transfer_number')

class StockAdjustmentAdmin(admin.ModelAdmin):
    list_display = ('adjustment_number', 'warehouse', 'adjustment_type', 'adjustment_date', 'adjusted_by', 'tenant')
    list_filter = ('adjustment_type', 'adjustment_date', 'warehouse', 'tenant')
    search_fields = ('adjustment_number', 'reason')

class StockAdjustmentItemAdmin(admin.ModelAdmin):
    list_display = ('stock_adjustment', 'product', 'quantity', 'tenant')
    list_filter = ('tenant',)
    search_fields = ('product__name', 'stock_adjustment__adjustment_number')

class StaffAttendanceAdmin(admin.ModelAdmin):
    list_display = ('staff', 'date', 'check_in_time', 'check_out_time', 'tenant')
    list_filter = ('date', 'tenant')
    search_fields = ('staff__user__username', 'staff__user__first_name')

class SaleReturnAdmin(admin.ModelAdmin):
    list_display = ('return_number', 'sale', 'customer', 'return_date', 'return_type', 'refund_amount', 'status', 'tenant')
    list_filter = ('return_type', 'status', 'return_date', 'tenant')
    search_fields = ('return_number', 'sale__invoice_number', 'customer__name')
    readonly_fields = ('return_number', 'return_date', 'processed_at')

class SaleReturnItemAdmin(admin.ModelAdmin):
    list_display = ('sale_return', 'product', 'quantity', 'unit_price', 'total_price', 'tenant')
    list_filter = ('tenant',)
    search_fields = ('product__name', 'sale_return__return_number')

# Register with secure_admin_site
secure_admin_site.register(ProductCategory, ProductCategoryAdmin)
secure_admin_site.register(Supplier, SupplierAdmin)
secure_admin_site.register(Product, ProductAdmin)
secure_admin_site.register(Warehouse, WarehouseAdmin)
secure_admin_site.register(Inventory, InventoryAdmin)
secure_admin_site.register(PriceList, PriceListAdmin)
secure_admin_site.register(PriceListItem, PriceListItemAdmin)
secure_admin_site.register(Customer, CustomerAdmin)
secure_admin_site.register(PurchaseOrder, PurchaseOrderAdmin)
secure_admin_site.register(PurchaseOrderItem, PurchaseOrderItemAdmin)
secure_admin_site.register(GoodsReceipt, GoodsReceiptAdmin)
secure_admin_site.register(GoodsReceiptItem, GoodsReceiptItemAdmin)
secure_admin_site.register(Sale, SaleAdmin)
secure_admin_site.register(SaleItem, SaleItemAdmin)
secure_admin_site.register(StockTransfer, StockTransferAdmin)
secure_admin_site.register(StockTransferItem, StockTransferItemAdmin)
secure_admin_site.register(StockAdjustment, StockAdjustmentAdmin)
secure_admin_site.register(StockAdjustmentItem, StockAdjustmentItemAdmin)
secure_admin_site.register(StaffAttendance, StaffAttendanceAdmin)
secure_admin_site.register(SaleReturn, SaleReturnAdmin)
secure_admin_site.register(SaleReturnItem, SaleReturnItemAdmin)

class QuotationItemInline(admin.TabularInline):
    model = QuotationItem
    extra = 1
    fields = ('product', 'quantity', 'unit_price', 'total_price', 'notes')
    autocomplete_fields = ['product']
    readonly_fields = ('total_price',)

class QuotationAdmin(admin.ModelAdmin):
    list_display = ('quotation_number', 'customer', 'quotation_date', 'valid_until', 'status', 'total_amount', 'converted_to_sale', 'tenant')
    list_filter = ('status', 'quotation_date', 'customer__customer_type', 'tenant')
    search_fields = ('quotation_number', 'customer__name', 'customer__phone')
    readonly_fields = ('quotation_number', 'quotation_date', 'conversion_date', 'converted_to_sale')
    inlines = [QuotationItemInline]
    fieldsets = (
        ('Basic Information', {
            'fields': ('quotation_number', 'customer', 'tenant', 'quotation_date', 'valid_until')
        }),
        ('Status', {
            'fields': ('status', 'converted_to_sale', 'conversion_date')
        }),
        ('Financial Details', {
            'fields': ('subtotal', 'tax_amount', 'discount_amount', 'discount_percentage', 'total_amount')
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_by')
        }),
    )

class QuotationItemAdmin(admin.ModelAdmin):
    list_display = ('quotation', 'product', 'quantity', 'unit_price', 'total_price', 'tenant')
    list_filter = ('tenant',)
    search_fields = ('quotation__quotation_number', 'product__name', 'product__sku')
    readonly_fields = ('total_price',)

secure_admin_site.register(Quotation, QuotationAdmin)
secure_admin_site.register(QuotationItem, QuotationItemAdmin) 