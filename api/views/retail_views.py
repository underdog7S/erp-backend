from rest_framework import status, generics, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import timedelta
import json
import csv
from django.http import HttpResponse
from io import BytesIO
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
except ImportError:
    pass

from api.models.user import Tenant, UserProfile
from retail.models import (
    ProductCategory, Supplier, Product, Warehouse, Inventory, Customer,
    PurchaseOrder, PurchaseOrderItem, GoodsReceipt, GoodsReceiptItem,
    Sale, SaleItem, StockTransfer, StockTransferItem, StockAdjustment,
    StockAdjustmentItem, StaffAttendance
)
from ..serializers import (
    ProductCategorySerializer, RetailSupplierSerializer as SupplierSerializer, ProductSerializer,
    WarehouseSerializer, InventorySerializer, RetailCustomerSerializer as CustomerSerializer,
    RetailPurchaseOrderSerializer as PurchaseOrderSerializer, RetailPurchaseOrderItemSerializer as PurchaseOrderItemSerializer, GoodsReceiptSerializer,
    GoodsReceiptItemSerializer, RetailSaleSerializer as SaleSerializer, RetailSaleItemSerializer as SaleItemSerializer,
    StockTransferSerializer, StockTransferItemSerializer, RetailStockAdjustmentSerializer as StockAdjustmentSerializer,
    StockAdjustmentItemSerializer, RetailStaffAttendanceSerializer as StaffAttendanceSerializer
)

# Product Category Views
class ProductCategoryListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProductCategorySerializer
    
    def get_queryset(self):
        return ProductCategory.objects.filter(tenant=self.request.user.userprofile.tenant)
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.userprofile.tenant)

class ProductCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProductCategorySerializer
    
    def get_queryset(self):
        return ProductCategory.objects.filter(tenant=self.request.user.userprofile.tenant)

# Supplier Views
class SupplierListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SupplierSerializer
    
    def get_queryset(self):
        return Supplier.objects.filter(tenant=self.request.user.userprofile.tenant)
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.userprofile.tenant)

class SupplierDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SupplierSerializer
    
    def get_queryset(self):
        return Supplier.objects.filter(tenant=self.request.user.userprofile.tenant)

# Warehouse Views
class WarehouseListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = WarehouseSerializer
    
    def get_queryset(self):
        return Warehouse.objects.filter(tenant=self.request.user.userprofile.tenant)
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.userprofile.tenant)

class WarehouseDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = WarehouseSerializer
    
    def get_queryset(self):
        return Warehouse.objects.filter(tenant=self.request.user.userprofile.tenant)

# Product Views
class ProductListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProductSerializer
    parser_classes = [MultiPartParser, FormParser]
    
    def get_queryset(self):
        queryset = Product.objects.filter(tenant=self.request.user.userprofile.tenant)
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category_id=category)
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.userprofile.tenant)

class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProductSerializer
    parser_classes = [MultiPartParser, FormParser]
    
    def get_queryset(self):
        return Product.objects.filter(tenant=self.request.user.userprofile.tenant)

# Inventory Views
class InventoryListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = InventorySerializer
    
    def get_queryset(self):
        queryset = Inventory.objects.filter(tenant=self.request.user.userprofile.tenant)
        warehouse = self.request.query_params.get('warehouse', None)
        if warehouse:
            queryset = queryset.filter(warehouse_id=warehouse)
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.userprofile.tenant)

class InventoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = InventorySerializer
    
    def get_queryset(self):
        return Inventory.objects.filter(tenant=self.request.user.userprofile.tenant)

# Customer Views
class CustomerListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CustomerSerializer
    
    def get_queryset(self):
        queryset = Customer.objects.filter(tenant=self.request.user.userprofile.tenant)
        search = self.request.query_params.get('search', None)
        customer_type = self.request.query_params.get('customer_type', None)
        
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(phone__icontains=search) | 
                Q(email__icontains=search)
            )
        
        if customer_type:
            queryset = queryset.filter(customer_type=customer_type)
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.userprofile.tenant)

class CustomerDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CustomerSerializer
    
    def get_queryset(self):
        return Customer.objects.filter(tenant=self.request.user.userprofile.tenant)

# Purchase Order Views
class PurchaseOrderListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PurchaseOrderSerializer
    
    def get_queryset(self):
        queryset = PurchaseOrder.objects.filter(tenant=self.request.user.userprofile.tenant)
        supplier = self.request.query_params.get('supplier', None)
        status_filter = self.request.query_params.get('status', None)
        
        if supplier:
            queryset = queryset.filter(supplier_id=supplier)
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.userprofile.tenant, created_by=self.request.user.userprofile)

class PurchaseOrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PurchaseOrderSerializer
    
    def get_queryset(self):
        return PurchaseOrder.objects.filter(tenant=self.request.user.userprofile.tenant)

# Goods Receipt Views
class GoodsReceiptListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = GoodsReceiptSerializer
    
    def get_queryset(self):
        queryset = GoodsReceipt.objects.filter(tenant=self.request.user.userprofile.tenant)
        purchase_order = self.request.query_params.get('purchase_order', None)
        if purchase_order:
            queryset = queryset.filter(purchase_order_id=purchase_order)
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.userprofile.tenant, received_by=self.request.user.userprofile)

class GoodsReceiptDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = GoodsReceiptSerializer
    
    def get_queryset(self):
        return GoodsReceipt.objects.filter(tenant=self.request.user.userprofile.tenant)

# Sale Views
class SaleListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SaleSerializer
    
    def get_queryset(self):
        try:
            queryset = Sale.objects.filter(tenant=self.request.user.userprofile.tenant)
            customer = self.request.query_params.get('customer', None)
            warehouse = self.request.query_params.get('warehouse', None)
            
            if customer:
                queryset = queryset.filter(customer_id=customer)
            
            if warehouse:
                queryset = queryset.filter(warehouse_id=warehouse)
            
            return queryset
        except Exception as e:
            print(f"Error in SaleListCreateView.get_queryset: {e}")
            return Sale.objects.none()
    
    def perform_create(self, serializer):
        items_data = self.request.data.get('items', [])
        # Update the context with items data
        serializer._context.update({
            'items': items_data,
            'request': self.request
        })
        serializer.save(tenant=self.request.user.userprofile.tenant, sold_by=self.request.user.userprofile)

class SaleDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SaleSerializer
    
    def get_queryset(self):
        return Sale.objects.filter(tenant=self.request.user.userprofile.tenant)

# Stock Transfer Views
class StockTransferListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = StockTransferSerializer
    
    def get_queryset(self):
        queryset = StockTransfer.objects.filter(tenant=self.request.user.userprofile.tenant)
        status_filter = self.request.query_params.get('status', None)
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.userprofile.tenant, transferred_by=self.request.user.userprofile)

class StockTransferDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = StockTransferSerializer
    
    def get_queryset(self):
        return StockTransfer.objects.filter(tenant=self.request.user.userprofile.tenant)

# Stock Adjustment Views
class StockAdjustmentListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = StockAdjustmentSerializer
    
    def get_queryset(self):
        queryset = StockAdjustment.objects.filter(tenant=self.request.user.userprofile.tenant)
        warehouse = self.request.query_params.get('warehouse', None)
        adjustment_type = self.request.query_params.get('adjustment_type', None)
        
        if warehouse:
            queryset = queryset.filter(warehouse_id=warehouse)
        
        if adjustment_type:
            queryset = queryset.filter(adjustment_type=adjustment_type)
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.userprofile.tenant, adjusted_by=self.request.user.userprofile)

class StockAdjustmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = StockAdjustmentSerializer
    
    def get_queryset(self):
        return StockAdjustment.objects.filter(tenant=self.request.user.userprofile.tenant)

# Staff Attendance Views
class StaffAttendanceListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = StaffAttendanceSerializer
    
    def get_queryset(self):
        return StaffAttendance.objects.filter(tenant=self.request.user.userprofile.tenant)
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.userprofile.tenant)

class StaffAttendanceDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = StaffAttendanceSerializer
    
    def get_queryset(self):
        return StaffAttendance.objects.filter(tenant=self.request.user.userprofile.tenant)

# Analytics Views
class RetailAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        tenant = request.user.userprofile.tenant
        
        # Sales analytics
        today = timezone.now().date()
        month_start = today.replace(day=1)
        
        daily_sales = Sale.objects.filter(
            tenant=tenant,
            sale_date__date=today
        ).aggregate(
            total_sales=Sum('total_amount'),
            total_transactions=Count('id')
        )
        
        monthly_sales = Sale.objects.filter(
            tenant=tenant,
            sale_date__date__gte=month_start
        ).aggregate(
            total_sales=Sum('total_amount'),
            total_transactions=Count('id')
        )
        
        # Inventory analytics
        low_stock_products = Inventory.objects.filter(
            tenant=tenant,
            quantity_available__lte=10
        ).count()
        
        total_warehouses = Warehouse.objects.filter(tenant=tenant).count()
        
        # Customer analytics
        total_customers = Customer.objects.filter(tenant=tenant).count()
        retail_customers = Customer.objects.filter(tenant=tenant, customer_type='RETAIL').count()
        wholesale_customers = Customer.objects.filter(tenant=tenant, customer_type='WHOLESALE').count()
        
        return Response({
            'daily_sales': daily_sales,
            'monthly_sales': monthly_sales,
            'low_stock_products': low_stock_products,
            'total_warehouses': total_warehouses,
            'total_customers': total_customers,
            'retail_customers': retail_customers,
            'wholesale_customers': wholesale_customers,
        })

# Check-in/Check-out Views
class StaffAttendanceCheckInView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        staff = request.user.userprofile
        tenant = staff.tenant
        today = timezone.now().date()
        
        attendance, created = StaffAttendance.objects.get_or_create(
            staff=staff,
            date=today,
            tenant=tenant,
            defaults={'check_in_time': timezone.now()}
        )
        
        if not created and not attendance.check_in_time:
            attendance.check_in_time = timezone.now()
            attendance.save()
        
        return Response({
            'message': 'Check-in recorded successfully',
            'check_in_time': attendance.check_in_time
        })

class StaffAttendanceCheckOutView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        staff = request.user.userprofile
        tenant = staff.tenant
        today = timezone.now().date()
        
        try:
            attendance = StaffAttendance.objects.get(
                staff=staff,
                date=today,
                tenant=tenant
            )
            attendance.check_out_time = timezone.now()
            attendance.save()
            
            return Response({
                'message': 'Check-out recorded successfully',
                'check_out_time': attendance.check_out_time
            })
        except StaffAttendance.DoesNotExist:
            return Response({
                'error': 'No check-in record found for today'
            }, status=status.HTTP_400_BAD_REQUEST) 

class RetailProductExportView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        products = Product._default_manager.filter(tenant=profile.tenant)
        
        # Filtering
        category_id = request.query_params.get('category')
        search = request.query_params.get('search')
        supplier_id = request.query_params.get('supplier')
        
        if category_id:
            products = products.filter(category_id=category_id)
        if search:
            products = products.filter(
                Q(name__icontains=search) | 
                Q(description__icontains=search) |
                Q(sku__icontains=search)
            )
        if supplier_id:
            products = products.filter(supplier_id=supplier_id)
        
        export_format = request.query_params.get('format', 'csv').lower()
        
        if export_format == 'pdf':
            try:
                buffer = BytesIO()
                p = canvas.Canvas(buffer, pagesize=letter)
                width, height = letter
                y = height - 40
                p.setFont("Helvetica-Bold", 14)
                p.drawString(40, y, "Retail Products Report")
                y -= 30
                p.setFont("Helvetica", 8)
                headers = ["ID", "Name", "Category", "SKU", "Price", "Stock"]
                for i, h in enumerate(headers):
                    p.drawString(40 + i*80, y, h)
                y -= 20
                
                for product in products:
                    # Calculate total stock across all warehouses
                    total_stock = Inventory._default_manager.filter(
                        product=product, 
                        tenant=profile.tenant
                    ).aggregate(total=Sum('quantity'))['total'] or 0
                    
                    row = [
                        str(product.id),
                        product.name,
                        product.category.name if product.category else "N/A",
                        product.sku or "N/A",
                        f"₹{product.price}",
                        str(total_stock)
                    ]
                    for i, val in enumerate(row):
                        p.drawString(40 + i*80, y, val)
                    y -= 15
                    if y < 40:
                        p.showPage()
                        y = height - 40
                p.save()
                buffer.seek(0)
                response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename="retail_products.pdf"'
                return response
            except Exception as e:
                return Response({'error': f'PDF export failed: {str(e)}'}, status=500)
        else:
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="retail_products.csv"'
            writer = csv.writer(response)
            writer.writerow(["ID", "Name", "Category", "SKU", "Description", "Price", "Cost Price", "Supplier", "Barcode"])
            
            for product in products:
                # Calculate total stock across all warehouses
                total_stock = Inventory._default_manager.filter(
                    product=product, 
                    tenant=profile.tenant
                ).aggregate(total=Sum('quantity'))['total'] or 0
                
                writer.writerow([
                    product.id,
                    product.name,
                    product.category.name if product.category else "",
                    product.sku or "",
                    product.description or "",
                    product.price,
                    product.cost_price,
                    product.supplier.name if product.supplier else "",
                    product.barcode or ""
                ])
            return response

class RetailSaleExportView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        sales = Sale._default_manager.filter(tenant=profile.tenant)
        
        # Filtering
        customer_id = request.query_params.get('customer')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        payment_method = request.query_params.get('payment_method')
        
        if customer_id:
            sales = sales.filter(customer_id=customer_id)
        if date_from:
            sales = sales.filter(sale_date__gte=date_from)
        if date_to:
            sales = sales.filter(sale_date__lte=date_to)
        if payment_method:
            sales = sales.filter(payment_method=payment_method)
        
        export_format = request.query_params.get('format', 'csv').lower()
        
        if export_format == 'pdf':
            try:
                buffer = BytesIO()
                p = canvas.Canvas(buffer, pagesize=letter)
                width, height = letter
                y = height - 40
                p.setFont("Helvetica-Bold", 14)
                p.drawString(40, y, "Retail Sales Report")
                y -= 30
                p.setFont("Helvetica", 8)
                headers = ["ID", "Customer", "Date", "Total", "Payment Method", "Status"]
                for i, h in enumerate(headers):
                    p.drawString(40 + i*80, y, h)
                y -= 20
                
                for sale in sales:
                    row = [
                        str(sale.id),
                        sale.customer.name if sale.customer else "Walk-in",
                        sale.sale_date.strftime('%Y-%m-%d'),
                        f"₹{sale.total_amount}",
                        sale.payment_method,
                        sale.status
                    ]
                    for i, val in enumerate(row):
                        p.drawString(40 + i*80, y, val)
                    y -= 15
                    if y < 40:
                        p.showPage()
                        y = height - 40
                p.save()
                buffer.seek(0)
                response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename="retail_sales.pdf"'
                return response
            except Exception as e:
                return Response({'error': f'PDF export failed: {str(e)}'}, status=500)
        else:
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="retail_sales.csv"'
            writer = csv.writer(response)
            writer.writerow(["ID", "Customer", "Customer Phone", "Sale Date", "Total Amount", "Payment Method", "Status", "Notes"])
            
            for sale in sales:
                writer.writerow([
                    sale.id,
                    sale.customer.name if sale.customer else "Walk-in",
                    sale.customer.phone if sale.customer else "",
                    sale.sale_date.strftime('%Y-%m-%d'),
                    sale.total_amount,
                    sale.payment_method,
                    sale.status,
                    sale.notes or ""
                ])
            return response

class RetailPurchaseOrderExportView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        purchase_orders = PurchaseOrder._default_manager.filter(tenant=profile.tenant)
        
        # Filtering
        supplier_id = request.query_params.get('supplier')
        status = request.query_params.get('status')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        if supplier_id:
            purchase_orders = purchase_orders.filter(supplier_id=supplier_id)
        if status:
            purchase_orders = purchase_orders.filter(status=status)
        if date_from:
            purchase_orders = purchase_orders.filter(order_date__gte=date_from)
        if date_to:
            purchase_orders = purchase_orders.filter(order_date__lte=date_to)
        
        export_format = request.query_params.get('format', 'csv').lower()
        
        if export_format == 'pdf':
            try:
                buffer = BytesIO()
                p = canvas.Canvas(buffer, pagesize=letter)
                width, height = letter
                y = height - 40
                p.setFont("Helvetica-Bold", 14)
                p.drawString(40, y, "Purchase Orders Report")
                y -= 30
                p.setFont("Helvetica", 8)
                headers = ["ID", "Supplier", "Order Date", "Total", "Status", "Expected Delivery"]
                for i, h in enumerate(headers):
                    p.drawString(40 + i*80, y, h)
                y -= 20
                
                for po in purchase_orders:
                    row = [
                        str(po.id),
                        po.supplier.name if po.supplier else "N/A",
                        po.order_date.strftime('%Y-%m-%d'),
                        f"₹{po.total_amount}",
                        po.status,
                        po.expected_delivery_date.strftime('%Y-%m-%d') if po.expected_delivery_date else "Not Set"
                    ]
                    for i, val in enumerate(row):
                        p.drawString(40 + i*80, y, val)
                    y -= 15
                    if y < 40:
                        p.showPage()
                        y = height - 40
                p.save()
                buffer.seek(0)
                response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename="purchase_orders.pdf"'
                return response
            except Exception as e:
                return Response({'error': f'PDF export failed: {str(e)}'}, status=500)
        else:
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="purchase_orders.csv"'
            writer = csv.writer(response)
            writer.writerow(["ID", "Supplier", "Supplier Contact", "Order Date", "Expected Delivery", "Total Amount", "Status", "Notes"])
            
            for po in purchase_orders:
                writer.writerow([
                    po.id,
                    po.supplier.name if po.supplier else "N/A",
                    po.supplier.contact_person if po.supplier else "",
                    po.order_date.strftime('%Y-%m-%d'),
                    po.expected_delivery_date.strftime('%Y-%m-%d') if po.expected_delivery_date else "",
                    po.total_amount,
                    po.status,
                    po.notes or ""
                ])
            return response

class RetailInventoryExportView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        inventory_items = Inventory._default_manager.filter(tenant=profile.tenant)
        
        # Filtering
        warehouse_id = request.query_params.get('warehouse')
        product_id = request.query_params.get('product')
        low_stock = request.query_params.get('low_stock')  # true/false
        
        if warehouse_id:
            inventory_items = inventory_items.filter(warehouse_id=warehouse_id)
        if product_id:
            inventory_items = inventory_items.filter(product_id=product_id)
        if low_stock == 'true':
            inventory_items = inventory_items.filter(quantity__lte=10)  # Assuming 10 is low stock threshold
        
        export_format = request.query_params.get('format', 'csv').lower()
        
        if export_format == 'pdf':
            try:
                buffer = BytesIO()
                p = canvas.Canvas(buffer, pagesize=letter)
                width, height = letter
                y = height - 40
                p.setFont("Helvetica-Bold", 14)
                p.drawString(40, y, "Retail Inventory Report")
                y -= 30
                p.setFont("Helvetica", 8)
                headers = ["Product", "Warehouse", "Quantity", "Min Stock", "Max Stock"]
                for i, h in enumerate(headers):
                    p.drawString(40 + i*80, y, h)
                y -= 20
                
                for item in inventory_items:
                    row = [
                        item.product.name,
                        item.warehouse.name if item.warehouse else "N/A",
                        str(item.quantity),
                        str(item.min_stock_level),
                        str(item.max_stock_level)
                    ]
                    for i, val in enumerate(row):
                        p.drawString(40 + i*80, y, val)
                    y -= 15
                    if y < 40:
                        p.showPage()
                        y = height - 40
                p.save()
                buffer.seek(0)
                response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename="retail_inventory.pdf"'
                return response
            except Exception as e:
                return Response({'error': f'PDF export failed: {str(e)}'}, status=500)
        else:
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="retail_inventory.csv"'
            writer = csv.writer(response)
            writer.writerow(["Product", "Product SKU", "Warehouse", "Quantity", "Min Stock Level", "Max Stock Level", "Last Updated"])
            
            for item in inventory_items:
                writer.writerow([
                    item.product.name,
                    item.product.sku or "",
                    item.warehouse.name if item.warehouse else "N/A",
                    item.quantity,
                    item.min_stock_level,
                    item.max_stock_level,
                    item.updated_at.strftime('%Y-%m-%d %H:%M') if item.updated_at else ""
                ])
            return response 