from django.contrib import admin
from .models import (
    MedicineCategory, Supplier, Medicine, MedicineBatch, Customer, 
    Prescription, PrescriptionItem, Sale, SaleItem, PurchaseOrder, 
    PurchaseOrderItem, StockAdjustment, StaffAttendance
)

@admin.register(MedicineCategory)
class MedicineCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant')
    list_filter = ('tenant',)
    search_fields = ('name',)

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'phone', 'email', 'tenant')
    list_filter = ('tenant',)
    search_fields = ('name', 'contact_person', 'phone')

@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = ('name', 'generic_name', 'category', 'manufacturer', 'strength', 'dosage_form', 'prescription_required', 'tenant')
    list_filter = ('category', 'dosage_form', 'prescription_required', 'tenant')
    search_fields = ('name', 'generic_name', 'manufacturer')

@admin.register(MedicineBatch)
class MedicineBatchAdmin(admin.ModelAdmin):
    list_display = ('medicine', 'batch_number', 'supplier', 'expiry_date', 'quantity_available', 'tenant')
    list_filter = ('supplier', 'expiry_date', 'tenant')
    search_fields = ('medicine__name', 'batch_number')

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email', 'date_of_birth', 'tenant')
    list_filter = ('tenant',)
    search_fields = ('name', 'phone', 'email')

@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ('customer', 'doctor_name', 'prescription_date', 'tenant')
    list_filter = ('prescription_date', 'tenant')
    search_fields = ('customer__name', 'doctor_name')

@admin.register(PrescriptionItem)
class PrescriptionItemAdmin(admin.ModelAdmin):
    list_display = ('prescription', 'medicine', 'dosage', 'quantity', 'tenant')
    list_filter = ('medicine', 'tenant')
    search_fields = ('medicine__name', 'prescription__customer__name')

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'customer', 'sale_date', 'total_amount', 'payment_status', 'tenant')
    list_filter = ('payment_status', 'payment_method', 'sale_date', 'tenant')
    search_fields = ('invoice_number', 'customer__name')

@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = ('sale', 'medicine_batch', 'quantity', 'unit_price', 'total_price', 'tenant')
    list_filter = ('tenant',)
    search_fields = ('medicine_batch__medicine__name', 'sale__invoice_number')

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('po_number', 'supplier', 'order_date', 'status', 'total_amount', 'tenant')
    list_filter = ('status', 'order_date', 'tenant')
    search_fields = ('po_number', 'supplier__name')

@admin.register(PurchaseOrderItem)
class PurchaseOrderItemAdmin(admin.ModelAdmin):
    list_display = ('purchase_order', 'medicine', 'quantity', 'unit_cost', 'total_cost', 'tenant')
    list_filter = ('tenant',)
    search_fields = ('medicine__name', 'purchase_order__po_number')

@admin.register(StockAdjustment)
class StockAdjustmentAdmin(admin.ModelAdmin):
    list_display = ('medicine_batch', 'adjustment_type', 'quantity', 'adjustment_date', 'adjusted_by', 'tenant')
    list_filter = ('adjustment_type', 'adjustment_date', 'tenant')
    search_fields = ('medicine_batch__medicine__name', 'reason')

@admin.register(StaffAttendance)
class StaffAttendanceAdmin(admin.ModelAdmin):
    list_display = ('staff', 'date', 'check_in_time', 'check_out_time', 'tenant')
    list_filter = ('date', 'tenant')
    search_fields = ('staff__user__username', 'staff__user__first_name') 