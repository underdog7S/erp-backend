from django.contrib import admin
from .models import (
    Supplier, Warehouse, RawMaterial, RawMaterialInventory, FinishedGood,
    FinishedGoodInventory, BillOfMaterial, BOMItem, ProductionOrder,
    QualityCheck, PurchaseOrder, PurchaseOrderItem, GoodsReceipt,
    GoodsReceiptItem, Customer, SalesOrder, SalesOrderItem,
)

admin.site.register(Supplier)
admin.site.register(Warehouse)
admin.site.register(RawMaterial)
admin.site.register(RawMaterialInventory)
admin.site.register(FinishedGood)
admin.site.register(FinishedGoodInventory)
admin.site.register(BillOfMaterial)
admin.site.register(BOMItem)
admin.site.register(ProductionOrder)
admin.site.register(QualityCheck)
admin.site.register(PurchaseOrder)
admin.site.register(PurchaseOrderItem)
admin.site.register(GoodsReceipt)
admin.site.register(GoodsReceiptItem)
admin.site.register(Customer)
admin.site.register(SalesOrder)
admin.site.register(SalesOrderItem)
