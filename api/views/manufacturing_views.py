from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.db.models import Q, F
from api.models.permissions import HasFeaturePermissionFactory
from manufacturing.models import (
    Supplier, Warehouse, RawMaterial, RawMaterialInventory, FinishedGood,
    FinishedGoodInventory, BillOfMaterial, BOMItem, ProductionOrder,
    QualityCheck, PurchaseOrder, PurchaseOrderItem, GoodsReceipt,
    GoodsReceiptItem, Customer, SalesOrder, SalesOrderItem,
)
from api.serializers_manufacturing import (
    SupplierSerializer, WarehouseSerializer, RawMaterialSerializer,
    RawMaterialInventorySerializer, FinishedGoodSerializer,
    FinishedGoodInventorySerializer, BillOfMaterialSerializer, BOMItemSerializer,
    ProductionOrderSerializer, QualityCheckSerializer, PurchaseOrderSerializer,
    PurchaseOrderItemSerializer, GoodsReceiptSerializer, GoodsReceiptItemSerializer,
    CustomerSerializer, SalesOrderSerializer, SalesOrderItemSerializer,
)

FEATURE = 'manufacturing'


class SupplierListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory(FEATURE)]
    serializer_class = SupplierSerializer

    def get_queryset(self):
        return Supplier.objects.filter(tenant=self.request.user.userprofile.tenant)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.userprofile.tenant)


class SupplierDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory(FEATURE)]
    serializer_class = SupplierSerializer

    def get_queryset(self):
        return Supplier.objects.filter(tenant=self.request.user.userprofile.tenant)


class WarehouseListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory(FEATURE)]
    serializer_class = WarehouseSerializer

    def get_queryset(self):
        return Warehouse.objects.filter(tenant=self.request.user.userprofile.tenant)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.userprofile.tenant)


class WarehouseDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory(FEATURE)]
    serializer_class = WarehouseSerializer

    def get_queryset(self):
        return Warehouse.objects.filter(tenant=self.request.user.userprofile.tenant)


class RawMaterialListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory(FEATURE)]
    serializer_class = RawMaterialSerializer

    def get_queryset(self):
        queryset = RawMaterial.objects.filter(tenant=self.request.user.userprofile.tenant)
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(sku__icontains=search))
        return queryset

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.userprofile.tenant)


class RawMaterialDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory(FEATURE)]
    serializer_class = RawMaterialSerializer

    def get_queryset(self):
        return RawMaterial.objects.filter(tenant=self.request.user.userprofile.tenant)


class RawMaterialInventoryListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory(FEATURE)]
    serializer_class = RawMaterialInventorySerializer

    def get_queryset(self):
        queryset = RawMaterialInventory.objects.filter(tenant=self.request.user.userprofile.tenant).select_related('raw_material', 'warehouse').order_by('id')
        warehouse = self.request.query_params.get('warehouse')
        low_stock = self.request.query_params.get('low_stock')
        if warehouse:
            queryset = queryset.filter(warehouse_id=warehouse)
        if low_stock:
            queryset = queryset.filter(quantity_available__lte=F('raw_material__reorder_level'))
        return queryset

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.userprofile.tenant)


class RawMaterialInventoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory(FEATURE)]
    serializer_class = RawMaterialInventorySerializer

    def get_queryset(self):
        return RawMaterialInventory.objects.filter(tenant=self.request.user.userprofile.tenant)


class FinishedGoodListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory(FEATURE)]
    serializer_class = FinishedGoodSerializer

    def get_queryset(self):
        queryset = FinishedGood.objects.filter(tenant=self.request.user.userprofile.tenant)
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(sku__icontains=search))
        return queryset

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.userprofile.tenant)


class FinishedGoodDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory(FEATURE)]
    serializer_class = FinishedGoodSerializer

    def get_queryset(self):
        return FinishedGood.objects.filter(tenant=self.request.user.userprofile.tenant)


class FinishedGoodInventoryListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory(FEATURE)]
    serializer_class = FinishedGoodInventorySerializer

    def get_queryset(self):
        queryset = FinishedGoodInventory.objects.filter(tenant=self.request.user.userprofile.tenant).select_related('finished_good', 'warehouse').order_by('id')
        warehouse = self.request.query_params.get('warehouse')
        low_stock = self.request.query_params.get('low_stock')
        if warehouse:
            queryset = queryset.filter(warehouse_id=warehouse)
        if low_stock:
            queryset = queryset.filter(quantity_available__lte=F('finished_good__reorder_level'))
        return queryset

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.userprofile.tenant)


class FinishedGoodInventoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory(FEATURE)]
    serializer_class = FinishedGoodInventorySerializer

    def get_queryset(self):
        return FinishedGoodInventory.objects.filter(tenant=self.request.user.userprofile.tenant)


class BillOfMaterialListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory(FEATURE)]
    serializer_class = BillOfMaterialSerializer

    def get_queryset(self):
        queryset = BillOfMaterial.objects.filter(tenant=self.request.user.userprofile.tenant).select_related('finished_good').prefetch_related('items__raw_material')
        finished_good = self.request.query_params.get('finished_good')
        if finished_good:
            queryset = queryset.filter(finished_good_id=finished_good)
        return queryset

    def perform_create(self, serializer):
        tenant = self.request.user.userprofile.tenant
        finished_good = serializer.validated_data.get('finished_good')
        # Only one active BOM per finished good - deactivate the rest so a
        # new version becomes the one Production Orders use going forward.
        if serializer.validated_data.get('is_active', True):
            BillOfMaterial.objects.filter(tenant=tenant, finished_good=finished_good, is_active=True).update(is_active=False)
        last_version = BillOfMaterial.objects.filter(tenant=tenant, finished_good=finished_good).order_by('-version').first()
        next_version = (last_version.version + 1) if last_version else 1
        serializer.save(tenant=tenant, created_by=self.request.user.userprofile, version=next_version)


class BillOfMaterialDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory(FEATURE)]
    serializer_class = BillOfMaterialSerializer

    def get_queryset(self):
        return BillOfMaterial.objects.filter(tenant=self.request.user.userprofile.tenant).prefetch_related('items__raw_material')


class BOMItemListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory(FEATURE)]
    serializer_class = BOMItemSerializer

    def get_queryset(self):
        queryset = BOMItem.objects.filter(tenant=self.request.user.userprofile.tenant).select_related('raw_material')
        bom = self.request.query_params.get('bom')
        if bom:
            queryset = queryset.filter(bom_id=bom)
        return queryset

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.userprofile.tenant)


class BOMItemDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory(FEATURE)]
    serializer_class = BOMItemSerializer

    def get_queryset(self):
        return BOMItem.objects.filter(tenant=self.request.user.userprofile.tenant)


class ProductionOrderListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory(FEATURE)]
    serializer_class = ProductionOrderSerializer

    def get_queryset(self):
        queryset = ProductionOrder.objects.filter(tenant=self.request.user.userprofile.tenant).select_related(
            'finished_good', 'bom', 'raw_material_warehouse', 'output_warehouse', 'created_by', 'created_by__user'
        ).prefetch_related('quality_checks')
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.userprofile.tenant, created_by=self.request.user.userprofile)


class ProductionOrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory(FEATURE)]
    serializer_class = ProductionOrderSerializer

    def get_queryset(self):
        return ProductionOrder.objects.filter(tenant=self.request.user.userprofile.tenant).prefetch_related('quality_checks')


class ProductionOrderStartView(APIView):
    """Consumes raw materials per the BOM and moves the order to IN_PROGRESS."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory(FEATURE)]

    def post(self, request, pk):
        try:
            order = ProductionOrder.objects.get(pk=pk, tenant=request.user.userprofile.tenant)
        except ProductionOrder.DoesNotExist:
            return Response({'error': 'Production order not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            order.start_production()
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(ProductionOrderSerializer(order).data)


class ProductionOrderCompleteView(APIView):
    """Adds the produced quantity to finished goods inventory and marks COMPLETED.
    Optionally accepts {"quantity_produced": N} to record a different actual
    yield than planned (wastage, over-production, etc.)."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory(FEATURE)]

    def post(self, request, pk):
        try:
            order = ProductionOrder.objects.get(pk=pk, tenant=request.user.userprofile.tenant)
        except ProductionOrder.DoesNotExist:
            return Response({'error': 'Production order not found'}, status=status.HTTP_404_NOT_FOUND)

        quantity_produced = request.data.get('quantity_produced')
        try:
            order.complete_production(quantity_produced=quantity_produced)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(ProductionOrderSerializer(order).data)


class QualityCheckListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory(FEATURE)]
    serializer_class = QualityCheckSerializer

    def get_queryset(self):
        queryset = QualityCheck.objects.filter(tenant=self.request.user.userprofile.tenant)
        production_order = self.request.query_params.get('production_order')
        if production_order:
            queryset = queryset.filter(production_order_id=production_order)
        return queryset

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.userprofile.tenant, checked_by=self.request.user.userprofile)


class QualityCheckDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory(FEATURE)]
    serializer_class = QualityCheckSerializer

    def get_queryset(self):
        return QualityCheck.objects.filter(tenant=self.request.user.userprofile.tenant)


class PurchaseOrderListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory(FEATURE)]
    serializer_class = PurchaseOrderSerializer

    def get_queryset(self):
        queryset = PurchaseOrder.objects.filter(tenant=self.request.user.userprofile.tenant).select_related('supplier', 'created_by', 'created_by__user').prefetch_related('items')
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.userprofile.tenant, created_by=self.request.user.userprofile)


class PurchaseOrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory(FEATURE)]
    serializer_class = PurchaseOrderSerializer

    def get_queryset(self):
        return PurchaseOrder.objects.filter(tenant=self.request.user.userprofile.tenant).prefetch_related('items')


class PurchaseOrderItemListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory(FEATURE)]
    serializer_class = PurchaseOrderItemSerializer

    def get_queryset(self):
        queryset = PurchaseOrderItem.objects.filter(tenant=self.request.user.userprofile.tenant).select_related('raw_material')
        po = self.request.query_params.get('purchase_order')
        if po:
            queryset = queryset.filter(purchase_order_id=po)
        return queryset

    def perform_create(self, serializer):
        item = serializer.save(tenant=self.request.user.userprofile.tenant)
        po = item.purchase_order
        po.subtotal = sum((i.total_cost for i in po.items.all()), start=0)
        po.total_amount = po.subtotal + po.tax_amount
        po.save(update_fields=['subtotal', 'total_amount'])


class PurchaseOrderItemDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory(FEATURE)]
    serializer_class = PurchaseOrderItemSerializer

    def get_queryset(self):
        return PurchaseOrderItem.objects.filter(tenant=self.request.user.userprofile.tenant)


class GoodsReceiptListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory(FEATURE)]
    serializer_class = GoodsReceiptSerializer

    def get_queryset(self):
        return GoodsReceipt.objects.filter(tenant=self.request.user.userprofile.tenant).select_related('purchase_order', 'warehouse', 'received_by', 'received_by__user').prefetch_related('items')

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.userprofile.tenant, received_by=self.request.user.userprofile)


class GoodsReceiptDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory(FEATURE)]
    serializer_class = GoodsReceiptSerializer

    def get_queryset(self):
        return GoodsReceipt.objects.filter(tenant=self.request.user.userprofile.tenant).prefetch_related('items')


class GoodsReceiptItemListCreateView(generics.ListCreateAPIView):
    """Receiving a line item here is what actually moves stock: it credits
    RawMaterialInventory at the receipt's warehouse and rolls the received
    quantity up into the Purchase Order's status."""
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory(FEATURE)]
    serializer_class = GoodsReceiptItemSerializer

    def get_queryset(self):
        queryset = GoodsReceiptItem.objects.filter(tenant=self.request.user.userprofile.tenant).select_related('purchase_order_item__raw_material')
        gr = self.request.query_params.get('goods_receipt')
        if gr:
            queryset = queryset.filter(goods_receipt_id=gr)
        return queryset

    def perform_create(self, serializer):
        tenant = self.request.user.userprofile.tenant
        item = serializer.save(tenant=tenant)

        poi = item.purchase_order_item
        poi.received_quantity = F('received_quantity') + item.quantity_received
        poi.save(update_fields=['received_quantity'])
        poi.refresh_from_db()

        inv, _ = RawMaterialInventory.objects.get_or_create(
            raw_material=poi.raw_material, warehouse=item.goods_receipt.warehouse, tenant=tenant
        )
        inv.quantity_on_hand = F('quantity_on_hand') + item.quantity_received
        inv.save()

        po = poi.purchase_order
        all_items = list(po.items.all())
        if all(i.received_quantity >= i.quantity for i in all_items):
            po.status = 'RECEIVED'
        elif any(i.received_quantity > 0 for i in all_items):
            po.status = 'PARTIAL_RECEIVED'
        po.save(update_fields=['status'])


class GoodsReceiptItemDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory(FEATURE)]
    serializer_class = GoodsReceiptItemSerializer

    def get_queryset(self):
        return GoodsReceiptItem.objects.filter(tenant=self.request.user.userprofile.tenant)


class CustomerListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory(FEATURE)]
    serializer_class = CustomerSerializer

    def get_queryset(self):
        queryset = Customer.objects.filter(tenant=self.request.user.userprofile.tenant)
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(phone__icontains=search))
        return queryset

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.userprofile.tenant)


class CustomerDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory(FEATURE)]
    serializer_class = CustomerSerializer

    def get_queryset(self):
        return Customer.objects.filter(tenant=self.request.user.userprofile.tenant)


class SalesOrderListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory(FEATURE)]
    serializer_class = SalesOrderSerializer

    def get_queryset(self):
        queryset = SalesOrder.objects.filter(tenant=self.request.user.userprofile.tenant).select_related('customer', 'warehouse', 'created_by', 'created_by__user').prefetch_related('items')
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.userprofile.tenant, created_by=self.request.user.userprofile)


class SalesOrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory(FEATURE)]
    serializer_class = SalesOrderSerializer

    def get_queryset(self):
        return SalesOrder.objects.filter(tenant=self.request.user.userprofile.tenant).prefetch_related('items')


class SalesOrderItemListCreateView(generics.ListCreateAPIView):
    """Adding a line item here reserves stock: it decrements
    FinishedGoodInventory at the order's warehouse immediately, rather than
    waiting for a separate dispatch step - matches how Retail's Sale does it."""
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory(FEATURE)]
    serializer_class = SalesOrderItemSerializer

    def get_queryset(self):
        queryset = SalesOrderItem.objects.filter(tenant=self.request.user.userprofile.tenant).select_related('finished_good')
        so = self.request.query_params.get('sales_order')
        if so:
            queryset = queryset.filter(sales_order_id=so)
        return queryset

    def perform_create(self, serializer):
        tenant = self.request.user.userprofile.tenant
        item = serializer.save(tenant=tenant)

        so = item.sales_order
        inv = FinishedGoodInventory.objects.filter(finished_good=item.finished_good, warehouse=so.warehouse, tenant=tenant).first()
        if inv:
            inv.quantity_on_hand = F('quantity_on_hand') - item.quantity
            inv.save()

        # Snapshot the item's GST, then re-total the order. Business-to-business prices are ex-GST.
        from api.gst import line_tax, is_intra_state, split_cgst_sgst
        rate = item.finished_good.gst_rate
        _, item_tax = line_tax(item.total_price, rate, inclusive=False)
        SalesOrderItem.objects.filter(pk=item.pk).update(hsn_code=item.finished_good.hsn_code, gst_rate=rate, tax_amount=item_tax)

        so.subtotal = sum((i.total_price for i in so.items.all()), start=0)
        tax = sum((i.tax_amount for i in so.items.all()), start=0)
        if is_intra_state(tenant.gstin, so.customer.gst_number):
            so.cgst_amount, so.sgst_amount = split_cgst_sgst(tax)
            so.igst_amount = 0
        else:
            so.cgst_amount = so.sgst_amount = 0
            so.igst_amount = tax
        so.tax_amount = tax
        so.total_amount = so.subtotal + so.tax_amount - so.discount_amount
        so.save(update_fields=['subtotal', 'tax_amount', 'cgst_amount', 'sgst_amount', 'igst_amount', 'total_amount'])


class SalesOrderItemDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory(FEATURE)]
    serializer_class = SalesOrderItemSerializer

    def get_queryset(self):
        return SalesOrderItem.objects.filter(tenant=self.request.user.userprofile.tenant)


class ManufacturingOverviewView(APIView):
    """Summary stats for the dashboard's Overview tab."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory(FEATURE)]

    def get(self, request):
        tenant = request.user.userprofile.tenant

        raw_material_low_stock = RawMaterialInventory.objects.filter(
            tenant=tenant, quantity_available__lte=F('raw_material__reorder_level')
        ).select_related('raw_material', 'warehouse')[:10]

        finished_good_low_stock = FinishedGoodInventory.objects.filter(
            tenant=tenant, quantity_available__lte=F('finished_good__reorder_level')
        ).select_related('finished_good', 'warehouse')[:10]

        return Response({
            'raw_material_count': RawMaterial.objects.filter(tenant=tenant, is_active=True).count(),
            'finished_good_count': FinishedGood.objects.filter(tenant=tenant, is_active=True).count(),
            'active_bom_count': BillOfMaterial.objects.filter(tenant=tenant, is_active=True).count(),
            'production_orders_planned': ProductionOrder.objects.filter(tenant=tenant, status='PLANNED').count(),
            'production_orders_in_progress': ProductionOrder.objects.filter(tenant=tenant, status='IN_PROGRESS').count(),
            'production_orders_completed': ProductionOrder.objects.filter(tenant=tenant, status='COMPLETED').count(),
            'pending_purchase_orders': PurchaseOrder.objects.filter(tenant=tenant, status__in=['DRAFT', 'ORDERED', 'PARTIAL_RECEIVED']).count(),
            'pending_sales_orders': SalesOrder.objects.filter(tenant=tenant, status__in=['DRAFT', 'CONFIRMED']).count(),
            'quality_checks_pending': QualityCheck.objects.filter(tenant=tenant, result='PENDING').count(),
            'quality_checks_failed': QualityCheck.objects.filter(tenant=tenant, result='FAILED').count(),
            'raw_material_low_stock': [{
                'raw_material': i.raw_material.name, 'warehouse': i.warehouse.name,
                'available': i.quantity_available, 'reorder_level': i.raw_material.reorder_level,
            } for i in raw_material_low_stock],
            'finished_good_low_stock': [{
                'finished_good': i.finished_good.name, 'warehouse': i.warehouse.name,
                'available': i.quantity_available, 'reorder_level': i.finished_good.reorder_level,
            } for i in finished_good_low_stock],
        })
