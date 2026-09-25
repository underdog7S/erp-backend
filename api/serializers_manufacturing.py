from rest_framework import serializers
from manufacturing.models import (
    Supplier, Warehouse, RawMaterial, RawMaterialInventory, FinishedGood,
    FinishedGoodInventory, BillOfMaterial, BOMItem, ProductionOrder,
    QualityCheck, PurchaseOrder, PurchaseOrderItem, GoodsReceipt,
    GoodsReceiptItem, Customer, SalesOrder, SalesOrderItem,
)

class TenantModelSerializer(serializers.ModelSerializer):
    """Refuses any related record (supplier, warehouse, order...) that belongs to another business."""

    def validate(self, attrs):
        request = self.context.get('request')
        profile = getattr(getattr(request, 'user', None), 'userprofile', None)
        if profile:
            for name, value in attrs.items():
                if hasattr(value, 'tenant_id') and value.tenant_id != profile.tenant_id:
                    raise serializers.ValidationError({name: 'Unknown record.'})
        return super().validate(attrs)



class SupplierSerializer(TenantModelSerializer):
    # Explicit default: DRF's BooleanField treats an absent field in
    # multipart/form data as False (HTML checkbox semantics) rather than
    # falling back to the model's default=True, so omitting is_active from
    # a create request would otherwise silently create an inactive supplier.
    is_active = serializers.BooleanField(default=True)

    class Meta:
        model = Supplier
        fields = '__all__'
        read_only_fields = ('tenant',)


class WarehouseSerializer(TenantModelSerializer):
    class Meta:
        model = Warehouse
        fields = '__all__'
        read_only_fields = ('tenant',)


class RawMaterialSerializer(TenantModelSerializer):
    preferred_supplier_name = serializers.CharField(source='preferred_supplier.name', read_only=True, allow_null=True)
    is_active = serializers.BooleanField(default=True)  # see SupplierSerializer for why this is explicit

    class Meta:
        model = RawMaterial
        fields = '__all__'
        read_only_fields = ('tenant', 'sku')


class RawMaterialInventorySerializer(TenantModelSerializer):
    raw_material_name = serializers.CharField(source='raw_material.name', read_only=True)
    raw_material_sku = serializers.CharField(source='raw_material.sku', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)

    class Meta:
        model = RawMaterialInventory
        fields = '__all__'
        read_only_fields = ('tenant', 'quantity_available')


class FinishedGoodSerializer(TenantModelSerializer):
    is_active = serializers.BooleanField(default=True)  # see SupplierSerializer for why this is explicit

    class Meta:
        model = FinishedGood
        fields = '__all__'
        read_only_fields = ('tenant', 'sku')


class FinishedGoodInventorySerializer(TenantModelSerializer):
    finished_good_name = serializers.CharField(source='finished_good.name', read_only=True)
    finished_good_sku = serializers.CharField(source='finished_good.sku', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)

    class Meta:
        model = FinishedGoodInventory
        fields = '__all__'
        read_only_fields = ('tenant', 'quantity_available')


class BOMItemSerializer(TenantModelSerializer):
    raw_material_name = serializers.CharField(source='raw_material.name', read_only=True)
    raw_material_sku = serializers.CharField(source='raw_material.sku', read_only=True)
    unit_of_measure = serializers.CharField(source='raw_material.unit_of_measure', read_only=True)

    class Meta:
        model = BOMItem
        fields = '__all__'
        read_only_fields = ('tenant',)


class BillOfMaterialSerializer(TenantModelSerializer):
    items = BOMItemSerializer(many=True, read_only=True)
    finished_good_name = serializers.CharField(source='finished_good.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.user.username', read_only=True, allow_null=True)
    estimated_unit_cost = serializers.SerializerMethodField()
    is_active = serializers.BooleanField(default=True)  # see SupplierSerializer for why this is explicit

    class Meta:
        model = BillOfMaterial
        fields = '__all__'
        read_only_fields = ('tenant', 'created_by')

    def get_estimated_unit_cost(self, obj):
        return obj.estimated_unit_cost()


class QualityCheckSerializer(TenantModelSerializer):
    checked_by_name = serializers.CharField(source='checked_by.user.username', read_only=True, allow_null=True)
    production_order_number = serializers.CharField(source='production_order.order_number', read_only=True, allow_null=True)

    class Meta:
        model = QualityCheck
        fields = '__all__'
        read_only_fields = ('tenant', 'checked_by')


class ProductionOrderSerializer(TenantModelSerializer):
    finished_good_name = serializers.CharField(source='finished_good.name', read_only=True)
    finished_good_sku = serializers.CharField(source='finished_good.sku', read_only=True)
    bom_version = serializers.IntegerField(source='bom.version', read_only=True)
    raw_material_warehouse_name = serializers.CharField(source='raw_material_warehouse.name', read_only=True)
    output_warehouse_name = serializers.CharField(source='output_warehouse.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.user.username', read_only=True, allow_null=True)
    quality_checks = QualityCheckSerializer(many=True, read_only=True)

    class Meta:
        model = ProductionOrder
        fields = '__all__'
        read_only_fields = ('tenant', 'order_number', 'quantity_produced', 'status', 'actual_start_date', 'actual_end_date', 'created_by')


class PurchaseOrderItemSerializer(TenantModelSerializer):
    raw_material_name = serializers.CharField(source='raw_material.name', read_only=True)

    class Meta:
        model = PurchaseOrderItem
        fields = '__all__'
        read_only_fields = ('tenant', 'total_cost')


class PurchaseOrderSerializer(TenantModelSerializer):
    items = PurchaseOrderItemSerializer(many=True, read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.user.username', read_only=True, allow_null=True)

    class Meta:
        model = PurchaseOrder
        fields = '__all__'
        read_only_fields = ('tenant', 'po_number', 'created_by')


class GoodsReceiptItemSerializer(TenantModelSerializer):
    raw_material_name = serializers.CharField(source='purchase_order_item.raw_material.name', read_only=True)

    class Meta:
        model = GoodsReceiptItem
        fields = '__all__'
        read_only_fields = ('tenant',)


class GoodsReceiptSerializer(TenantModelSerializer):
    items = GoodsReceiptItemSerializer(many=True, read_only=True)
    purchase_order_number = serializers.CharField(source='purchase_order.po_number', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    received_by_name = serializers.CharField(source='received_by.user.username', read_only=True, allow_null=True)

    class Meta:
        model = GoodsReceipt
        fields = '__all__'
        read_only_fields = ('tenant', 'gr_number', 'received_by')


class CustomerSerializer(TenantModelSerializer):
    class Meta:
        model = Customer
        fields = '__all__'
        read_only_fields = ('tenant',)


class SalesOrderItemSerializer(TenantModelSerializer):
    finished_good_name = serializers.CharField(source='finished_good.name', read_only=True)

    class Meta:
        model = SalesOrderItem
        fields = '__all__'
        read_only_fields = ('tenant', 'total_price')


class SalesOrderSerializer(TenantModelSerializer):
    items = SalesOrderItemSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.user.username', read_only=True, allow_null=True)

    class Meta:
        model = SalesOrder
        fields = '__all__'
        read_only_fields = ('tenant', 'so_number', 'created_by')
