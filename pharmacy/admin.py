from django.contrib import admin
from .models import (
    MedicineCategory, Supplier, Medicine, MedicineBatch, Customer, 
    Prescription, PrescriptionItem, Sale, SaleItem, PurchaseOrder, 
    PurchaseOrderItem, StockAdjustment, StaffAttendance
)
from api.admin_site import secure_admin_site

class MedicineCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant')
    list_filter = ('tenant',)
    search_fields = ('name',)

class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'phone', 'email', 'tenant')
    list_filter = ('tenant',)
    search_fields = ('name', 'contact_person', 'phone')

class MedicineAdmin(admin.ModelAdmin):
    list_display = ('name', 'generic_name', 'category', 'manufacturer', 'strength', 'dosage_form', 'prescription_required', 'tenant')
    list_filter = ('category', 'dosage_form', 'prescription_required', 'tenant')
    search_fields = ('name', 'generic_name', 'manufacturer')

class MedicineBatchAdmin(admin.ModelAdmin):
    list_display = ('medicine', 'batch_number', 'supplier', 'expiry_date', 'quantity_available', 'tenant')
    list_filter = ('supplier', 'expiry_date', 'tenant')
    search_fields = ('medicine__name', 'batch_number')

class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email', 'date_of_birth', 'tenant')
    list_filter = ('tenant',)
    search_fields = ('name', 'phone', 'email')

class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ('customer', 'doctor_name', 'prescription_date', 'tenant')
    list_filter = ('prescription_date', 'tenant')
    search_fields = ('customer__name', 'doctor_name')

class PrescriptionItemAdmin(admin.ModelAdmin):
    list_display = ('prescription', 'medicine', 'dosage', 'quantity', 'tenant')
    list_filter = ('medicine', 'tenant')
    search_fields = ('medicine__name', 'prescription__customer__name')

class SaleAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'customer', 'sale_date', 'total_amount', 'payment_status', 'tenant')
    list_filter = ('payment_status', 'payment_method', 'sale_date', 'tenant')
    search_fields = ('invoice_number', 'customer__name')

class SaleItemAdmin(admin.ModelAdmin):
    list_display = ('sale', 'medicine_batch', 'quantity', 'unit_price', 'total_price', 'tenant')
    list_filter = ('tenant',)
    search_fields = ('medicine_batch__medicine__name', 'sale__invoice_number')

class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('po_number', 'supplier', 'order_date', 'status', 'total_amount', 'tenant')
    list_filter = ('status', 'order_date', 'tenant')
    search_fields = ('po_number', 'supplier__name')

class PurchaseOrderItemAdmin(admin.ModelAdmin):
    list_display = ('purchase_order', 'medicine', 'quantity', 'unit_cost', 'total_cost', 'tenant')
    list_filter = ('tenant',)
    search_fields = ('medicine__name', 'purchase_order__po_number')

class StockAdjustmentAdmin(admin.ModelAdmin):
    list_display = ('medicine_batch', 'adjustment_type', 'quantity', 'adjustment_date', 'adjusted_by', 'tenant')
    list_filter = ('adjustment_type', 'adjustment_date', 'tenant')
    search_fields = ('medicine_batch__medicine__name', 'reason')

class StaffAttendanceAdmin(admin.ModelAdmin):
    list_display = ('staff', 'date', 'check_in_time', 'check_out_time', 'tenant')
    list_filter = ('date', 'tenant')
    search_fields = ('staff__user__username', 'staff__user__first_name')

# Register with secure_admin_site
secure_admin_site.register(MedicineCategory, MedicineCategoryAdmin)
secure_admin_site.register(Supplier, SupplierAdmin)
secure_admin_site.register(Medicine, MedicineAdmin)
secure_admin_site.register(MedicineBatch, MedicineBatchAdmin)
secure_admin_site.register(Customer, CustomerAdmin)
secure_admin_site.register(Prescription, PrescriptionAdmin)
secure_admin_site.register(PrescriptionItem, PrescriptionItemAdmin)
secure_admin_site.register(Sale, SaleAdmin)
secure_admin_site.register(SaleItem, SaleItemAdmin)
secure_admin_site.register(PurchaseOrder, PurchaseOrderAdmin)
secure_admin_site.register(PurchaseOrderItem, PurchaseOrderItemAdmin)
secure_admin_site.register(StockAdjustment, StockAdjustmentAdmin)
secure_admin_site.register(StaffAttendance, StaffAttendanceAdmin) 