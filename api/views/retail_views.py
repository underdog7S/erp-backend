from rest_framework import status, generics, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from api.models.permissions import HasFeaturePermissionFactory
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
    StockAdjustmentItem, StaffAttendance, SaleReturn, SaleReturnItem,
    PriceList, PriceListItem, Quotation, QuotationItem
)
from ..serializers import (
    ProductCategorySerializer, RetailSupplierSerializer as SupplierSerializer, ProductSerializer,
    WarehouseSerializer, InventorySerializer, RetailCustomerSerializer as CustomerSerializer,
    RetailPurchaseOrderSerializer as PurchaseOrderSerializer, RetailPurchaseOrderItemSerializer as PurchaseOrderItemSerializer, GoodsReceiptSerializer,
    GoodsReceiptItemSerializer, RetailSaleSerializer as SaleSerializer, RetailSaleItemSerializer as SaleItemSerializer,
    StockTransferSerializer, StockTransferItemSerializer, RetailStockAdjustmentSerializer as StockAdjustmentSerializer,
    StockAdjustmentItemSerializer, RetailStaffAttendanceSerializer as StaffAttendanceSerializer,
    RetailSaleReturnSerializer as SaleReturnSerializer, RetailSaleReturnItemSerializer as SaleReturnItemSerializer,
    RetailPriceListSerializer as PriceListSerializer, RetailPriceListItemSerializer as PriceListItemSerializer,
    RetailQuotationSerializer as QuotationSerializer, RetailQuotationItemSerializer as QuotationItemSerializer
)

# Product Category Views
class ProductCategoryListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail')]
    serializer_class = ProductCategorySerializer
    
    def get_queryset(self):
        return ProductCategory.objects.filter(tenant=self.request.user.userprofile.tenant)
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.userprofile.tenant)

class ProductCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail')]
    serializer_class = ProductCategorySerializer
    
    def get_queryset(self):
        return ProductCategory.objects.filter(tenant=self.request.user.userprofile.tenant)

# Supplier Views
class SupplierListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail')]
    serializer_class = SupplierSerializer
    
    def get_queryset(self):
        return Supplier.objects.filter(tenant=self.request.user.userprofile.tenant)
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.userprofile.tenant)

class SupplierDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail')]
    serializer_class = SupplierSerializer
    
    def get_queryset(self):
        return Supplier.objects.filter(tenant=self.request.user.userprofile.tenant)

# Warehouse Views
class WarehouseListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail')]
    serializer_class = WarehouseSerializer
    
    def get_queryset(self):
        return Warehouse.objects.filter(tenant=self.request.user.userprofile.tenant)
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.userprofile.tenant)

class WarehouseDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail')]
    serializer_class = WarehouseSerializer
    
    def get_queryset(self):
        return Warehouse.objects.filter(tenant=self.request.user.userprofile.tenant)

# Product Views
class ProductListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail')]
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
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail')]
    serializer_class = ProductSerializer
    parser_classes = [MultiPartParser, FormParser]
    
    def get_queryset(self):
        return Product.objects.filter(tenant=self.request.user.userprofile.tenant)

# Inventory Views
class InventoryListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail')]
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
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail')]
    serializer_class = InventorySerializer
    
    def get_queryset(self):
        return Inventory.objects.filter(tenant=self.request.user.userprofile.tenant)

# Customer Views
class CustomerListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail')]
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
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail')]
    serializer_class = CustomerSerializer
    
    def get_queryset(self):
        return Customer.objects.filter(tenant=self.request.user.userprofile.tenant)

# Price List Views
class PriceListListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail')]
    serializer_class = PriceListSerializer
    
    def get_queryset(self):
        queryset = PriceList.objects.filter(tenant=self.request.user.userprofile.tenant).prefetch_related('items')
        customer_type = self.request.query_params.get('customer_type', None)
        is_active = self.request.query_params.get('is_active', None)
        search = self.request.query_params.get('search', None)
        
        if customer_type:
            queryset = queryset.filter(customer_type__in=[customer_type, 'ALL'])
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        if search:
            queryset = queryset.filter(name__icontains=search)
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.userprofile.tenant)

class PriceListDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail')]
    serializer_class = PriceListSerializer
    
    def get_queryset(self):
        return PriceList.objects.filter(tenant=self.request.user.userprofile.tenant).prefetch_related('items')

class PriceListItemListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail')]
    serializer_class = PriceListItemSerializer
    
    def get_queryset(self):
        queryset = PriceListItem.objects.filter(tenant=self.request.user.userprofile.tenant).select_related('product', 'price_list')
        price_list = self.request.query_params.get('price_list', None)
        product = self.request.query_params.get('product', None)
        is_active = self.request.query_params.get('is_active', None)
        
        if price_list:
            queryset = queryset.filter(price_list_id=price_list)
        if product:
            queryset = queryset.filter(product_id=product)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.userprofile.tenant)

class PriceListItemDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail')]
    serializer_class = PriceListItemSerializer
    
    def get_queryset(self):
        return PriceListItem.objects.filter(tenant=self.request.user.userprofile.tenant).select_related('product', 'price_list')

class GetProductPriceView(APIView):
    """Get product price based on customer and quantity"""
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail')]
    
    def get(self, request):
        customer_id = request.query_params.get('customer')
        product_id = request.query_params.get('product')
        quantity = int(request.query_params.get('quantity', 1))
        
        if not customer_id or not product_id:
            return Response(
                {'error': 'customer and product parameters are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            customer = Customer.objects.get(id=customer_id, tenant=request.user.userprofile.tenant)
            product = Product.objects.get(id=product_id, tenant=request.user.userprofile.tenant)
            
            # Get price from customer's price list
            price = customer.get_product_price(product, quantity)
            
            return Response({
                'product_id': product.id,
                'product_name': product.name,
                'customer_id': customer.id,
                'customer_name': customer.name,
                'quantity': quantity,
                'price': float(price),
                'total': float(price * quantity),
                'price_list': customer.get_price_list().name if customer.get_price_list() else None
            })
        except Customer.DoesNotExist:
            return Response(
                {'error': 'Customer not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Product.DoesNotExist:
            return Response(
                {'error': 'Product not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# Quotation Views
class QuotationListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail')]
    serializer_class = QuotationSerializer
    
    def get_queryset(self):
        queryset = Quotation.objects.filter(tenant=self.request.user.userprofile.tenant).prefetch_related(
            'items__product',
            'customer',
            'created_by__user'
        )
        customer = self.request.query_params.get('customer', None)
        status_filter = self.request.query_params.get('status', None)
        customer_type = self.request.query_params.get('customer_type', None)
        search = self.request.query_params.get('search', None)
        date_from = self.request.query_params.get('date_from', None)
        date_to = self.request.query_params.get('date_to', None)
        
        if customer:
            queryset = queryset.filter(customer_id=customer)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if customer_type:
            queryset = queryset.filter(customer__customer_type=customer_type)
        if search:
            queryset = queryset.filter(
                Q(quotation_number__icontains=search) |
                Q(customer__name__icontains=search) |
                Q(customer__phone__icontains=search)
            )
        if date_from:
            queryset = queryset.filter(quotation_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(quotation_date__lte=date_to)
        
        return queryset.order_by('-quotation_date')
    
    def perform_create(self, serializer):
        items_data = self.request.data.get('items', [])
        tenant = self.request.user.userprofile.tenant
        
        # Generate quotation number if not provided
        if 'quotation_number' not in serializer.validated_data or not serializer.validated_data.get('quotation_number'):
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            quotation_number = f"QT{timestamp}"
            serializer.validated_data['quotation_number'] = quotation_number
        
        # Calculate totals from items
        subtotal = 0
        for item_data in items_data:
            quantity = item_data.get('quantity', 1)
            unit_price = item_data.get('unit_price', 0)
            subtotal += quantity * unit_price
        
        # Apply discount if provided
        discount_percentage = serializer.validated_data.get('discount_percentage', 0)
        discount_amount = (subtotal * discount_percentage / 100) if discount_percentage > 0 else serializer.validated_data.get('discount_amount', 0)
        
        # Calculate tax (assuming GST or similar)
        tax_rate = serializer.validated_data.get('tax_rate', 0)  # Can be passed in request
        tax_amount = (subtotal - discount_amount) * tax_rate / 100 if tax_rate > 0 else serializer.validated_data.get('tax_amount', 0)
        
        total_amount = subtotal - discount_amount + tax_amount
        
        serializer.validated_data['subtotal'] = subtotal
        serializer.validated_data['discount_amount'] = discount_amount
        serializer.validated_data['tax_amount'] = tax_amount
        serializer.validated_data['total_amount'] = total_amount
        
        quotation = serializer.save(tenant=tenant, created_by=self.request.user.userprofile)
        
        # Create quotation items
        for item_data in items_data:
            product_id = item_data.get('product')
            if product_id:
                try:
                    product = Product.objects.get(id=product_id, tenant=tenant)
                    QuotationItem.objects.create(
                        quotation=quotation,
                        product=product,
                        quantity=item_data.get('quantity', 1),
                        unit_price=item_data.get('unit_price', 0),
                        notes=item_data.get('notes', ''),
                        tenant=tenant
                    )
                except Product.DoesNotExist:
                    pass
        
        return quotation

class QuotationDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail')]
    serializer_class = QuotationSerializer
    
    def get_queryset(self):
        return Quotation.objects.filter(tenant=self.request.user.userprofile.tenant).prefetch_related('items__product')
    
    def perform_update(self, serializer):
        items_data = self.request.data.get('items', [])
        quotation = serializer.instance
        
        # Recalculate totals if items are updated
        if items_data:
            subtotal = 0
            for item_data in items_data:
                quantity = item_data.get('quantity', 1)
                unit_price = item_data.get('unit_price', 0)
                subtotal += quantity * unit_price
            
            discount_percentage = serializer.validated_data.get('discount_percentage', quotation.discount_percentage)
            discount_amount = (subtotal * discount_percentage / 100) if discount_percentage > 0 else serializer.validated_data.get('discount_amount', quotation.discount_amount)
            
            tax_amount = serializer.validated_data.get('tax_amount', quotation.tax_amount)
            total_amount = subtotal - discount_amount + tax_amount
            
            serializer.validated_data['subtotal'] = subtotal
            serializer.validated_data['discount_amount'] = discount_amount
            serializer.validated_data['total_amount'] = total_amount
        
        quotation = serializer.save()
        
        # Update items if provided
        if items_data:
            # Delete existing items
            QuotationItem.objects.filter(quotation=quotation).delete()
            
            # Create new items
            for item_data in items_data:
                product_id = item_data.get('product')
                if product_id:
                    try:
                        product = Product.objects.get(id=product_id, tenant=quotation.tenant)
                        QuotationItem.objects.create(
                            quotation=quotation,
                            product=product,
                            quantity=item_data.get('quantity', 1),
                            unit_price=item_data.get('unit_price', 0),
                            notes=item_data.get('notes', ''),
                            tenant=quotation.tenant
                        )
                    except Product.DoesNotExist:
                        pass
        
        return quotation

class ConvertQuotationToSaleView(APIView):
    """Convert an accepted quotation to a sale"""
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail')]
    
    def post(self, request, quotation_id):
        try:
            quotation = Quotation.objects.get(
                id=quotation_id,
                tenant=request.user.userprofile.tenant
            )
            
            if not quotation.can_convert_to_sale():
                return Response(
                    {'error': 'Quotation must be in ACCEPTED status to convert to sale'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if quotation.converted_to_sale:
                return Response(
                    {'error': 'Quotation has already been converted to sale'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get warehouse (use primary warehouse or first available)
            warehouse = Warehouse.objects.filter(
                tenant=request.user.userprofile.tenant,
                is_primary=True
            ).first()
            
            if not warehouse:
                warehouse = Warehouse.objects.filter(
                    tenant=request.user.userprofile.tenant
                ).first()
            
            if not warehouse:
                return Response(
                    {'error': 'No warehouse available. Please create a warehouse first.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Generate invoice number
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            invoice_number = f"RINV{timestamp}"
            
            # Create sale
            sale = Sale.objects.create(
                tenant=quotation.tenant,
                invoice_number=invoice_number,
                customer=quotation.customer,
                warehouse=warehouse,
                subtotal=quotation.subtotal,
                tax_amount=quotation.tax_amount,
                discount_amount=quotation.discount_amount,
                total_amount=quotation.total_amount,
                payment_method='CREDIT',  # Default for wholesale
                payment_status='PENDING',
                sold_by=request.user.userprofile,
                notes=f"Converted from Quotation {quotation.quotation_number}"
            )
            
            # Create sale items from quotation items
            for quotation_item in quotation.items.all():
                SaleItem.objects.create(
                    tenant=quotation.tenant,
                    sale=sale,
                    product=quotation_item.product,
                    quantity=quotation_item.quantity,
                    unit_price=quotation_item.unit_price,
                    total_price=quotation_item.total_price
                )
                
                # Update inventory (reduce stock)
                try:
                    inventory = Inventory.objects.get(
                        tenant=quotation.tenant,
                        product=quotation_item.product,
                        warehouse=warehouse
                    )
                    inventory.quantity_on_hand -= quotation_item.quantity
                    inventory.quantity_available = inventory.quantity_on_hand - inventory.quantity_reserved
                    inventory.save()
                except Inventory.DoesNotExist:
                    pass  # Inventory not found, skip stock update
            
            # Update quotation
            from django.utils import timezone
            quotation.status = 'CONVERTED'
            quotation.converted_to_sale = sale
            quotation.conversion_date = timezone.now()
            quotation.save()
            
            # Return sale data
            sale_serializer = SaleSerializer(sale)
            return Response({
                'message': 'Quotation converted to sale successfully',
                'sale': sale_serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except Quotation.DoesNotExist:
            return Response(
                {'error': 'Quotation not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# Purchase Order Views
class PurchaseOrderListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail')]
    serializer_class = PurchaseOrderSerializer
    
    def get_queryset(self):
        queryset = PurchaseOrder.objects.filter(tenant=self.request.user.userprofile.tenant)
        supplier = self.request.query_params.get('supplier', None)
        status_filter = self.request.query_params.get('status', None)
        search = self.request.query_params.get('search', None)
        date_from = self.request.query_params.get('date_from', None)
        date_to = self.request.query_params.get('date_to', None)
        
        if supplier:
            queryset = queryset.filter(supplier_id=supplier)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if search:
            queryset = queryset.filter(
                Q(po_number__icontains=search) |
                Q(supplier__name__icontains=search)
            )
        if date_from:
            queryset = queryset.filter(order_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(order_date__lte=date_to)
        
        return queryset.order_by('-order_date')
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.userprofile.tenant, created_by=self.request.user.userprofile)

class PurchaseOrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail')]
    serializer_class = PurchaseOrderSerializer
    
    def get_queryset(self):
        return PurchaseOrder.objects.filter(tenant=self.request.user.userprofile.tenant)

# Goods Receipt Views
class GoodsReceiptListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail')]
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
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail')]
    serializer_class = GoodsReceiptSerializer
    
    def get_queryset(self):
        return GoodsReceipt.objects.filter(tenant=self.request.user.userprofile.tenant)

# Sale Views
class SaleListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail')]
    serializer_class = SaleSerializer
    
    def get_queryset(self):
        try:
            queryset = Sale.objects.filter(tenant=self.request.user.userprofile.tenant).prefetch_related(
                'items__product',
                'customer',
                'warehouse',
                'sold_by__user'
            )
            customer = self.request.query_params.get('customer', None)
            warehouse = self.request.query_params.get('warehouse', None)
            search = self.request.query_params.get('search', None)
            payment_method = self.request.query_params.get('payment_method', None)
            payment_status = self.request.query_params.get('payment_status', None)
            customer_type = self.request.query_params.get('customer_type', None)
            date_from = self.request.query_params.get('date_from', None)
            date_to = self.request.query_params.get('date_to', None)
            
            if customer:
                queryset = queryset.filter(customer_id=customer)
            if warehouse:
                queryset = queryset.filter(warehouse_id=warehouse)
            if search:
                queryset = queryset.filter(
                    Q(invoice_number__icontains=search) |
                    Q(customer__name__icontains=search) |
                    Q(customer__phone__icontains=search)
                )
            if payment_method:
                queryset = queryset.filter(payment_method=payment_method)
            if payment_status:
                queryset = queryset.filter(payment_status=payment_status)
            if customer_type:
                queryset = queryset.filter(customer__customer_type=customer_type)
            if date_from:
                queryset = queryset.filter(sale_date__date__gte=date_from)
            if date_to:
                queryset = queryset.filter(sale_date__date__lte=date_to)
            
            return queryset.order_by('-sale_date')
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
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail')]
    serializer_class = SaleSerializer
    
    def get_queryset(self):
        return Sale.objects.filter(tenant=self.request.user.userprofile.tenant)

# Stock Transfer Views
class StockTransferListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail')]
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
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail')]
    serializer_class = StockTransferSerializer
    
    def get_queryset(self):
        return StockTransfer.objects.filter(tenant=self.request.user.userprofile.tenant)

# Stock Adjustment Views
class StockAdjustmentListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail')]
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
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail')]
    serializer_class = StockAdjustmentSerializer
    
    def get_queryset(self):
        return StockAdjustment.objects.filter(tenant=self.request.user.userprofile.tenant)

# Staff Attendance Views
class StaffAttendanceListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail')]
    serializer_class = StaffAttendanceSerializer
    
    def get_queryset(self):
        return StaffAttendance.objects.filter(tenant=self.request.user.userprofile.tenant)
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.userprofile.tenant)

class StaffAttendanceDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail')]
    serializer_class = StaffAttendanceSerializer
    
    def get_queryset(self):
        return StaffAttendance.objects.filter(tenant=self.request.user.userprofile.tenant)

# Analytics Views
class RetailAnalyticsView(APIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail'), HasFeaturePermissionFactory('analytics')]
    
    def get(self, request):
        tenant = request.user.userprofile.tenant
        
        # Sales analytics
        today = timezone.now().date()
        month_start = today.replace(day=1)
        thirty_days_ago = today - timedelta(days=30)
        
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
        
        # Profit margin calculation (selling_price - cost_price)
        from django.db.models import F
        recent_sales_items = SaleItem.objects.filter(
            tenant=tenant,
            sale__sale_date__date__gte=thirty_days_ago
        ).aggregate(
            total_revenue=Sum('total_price'),
            total_cost=Sum(F('product__cost_price') * F('quantity')),
            item_count=Count('id')
        )
        
        total_revenue = float(recent_sales_items['total_revenue'] or 0)
        total_cost = float(recent_sales_items['total_cost'] or 0)
        profit_margin = total_revenue - total_cost
        profit_percentage = (profit_margin / total_revenue * 100) if total_revenue > 0 else 0
        
        # Inventory analytics
        low_stock_products = Inventory.objects.filter(
            tenant=tenant,
            quantity_available__lte=F('product__reorder_level')
        ).count()
        
        out_of_stock_products = Inventory.objects.filter(
            tenant=tenant,
            quantity_available__lte=0
        ).count()
        
        total_warehouses = Warehouse.objects.filter(tenant=tenant).count()
        
        # Warehouse-wise inventory summary
        warehouse_inventory = Inventory.objects.filter(
            tenant=tenant
        ).values('warehouse__name').annotate(
            total_products=Count('product', distinct=True),
            total_quantity=Sum('quantity_available'),
            total_value=Sum(F('product__cost_price') * F('quantity_available'))
        )
        
        # Top selling products (last 30 days)
        top_products = SaleItem.objects.filter(
            tenant=tenant,
            sale__sale_date__date__gte=thirty_days_ago
        ).values(
            'product__name',
            'product__category__name'
        ).annotate(
            total_quantity=Sum('quantity'),
            total_revenue=Sum('total_price')
        ).order_by('-total_revenue')[:10]
        
        # Customer analytics
        total_customers = Customer.objects.filter(tenant=tenant).count()
        retail_customers = Customer.objects.filter(tenant=tenant, customer_type='RETAIL').count()
        wholesale_customers = Customer.objects.filter(tenant=tenant, customer_type='WHOLESALE').count()
        distributor_customers = Customer.objects.filter(tenant=tenant, customer_type='DISTRIBUTOR').count()
        
        recent_customers = Customer.objects.filter(
            tenant=tenant,
            created_at__date__gte=thirty_days_ago
        ).count()
        
        # Top customers by revenue
        top_customers = Sale.objects.filter(
            tenant=tenant,
            sale_date__date__gte=thirty_days_ago
        ).values(
            'customer__name',
            'customer__customer_type'
        ).annotate(
            total_purchases=Count('id'),
            total_revenue=Sum('total_amount')
        ).order_by('-total_revenue')[:10]
        
        # Product analytics
        total_products = Product.objects.filter(tenant=tenant).count()
        active_products = Product.objects.filter(tenant=tenant, is_active=True).count()
        
        # Stock value calculation
        total_stock_value = Inventory.objects.filter(
            tenant=tenant,
            quantity_available__gt=0
        ).aggregate(
            total_value=Sum(F('product__cost_price') * F('quantity_available'))
        )['total_value'] or 0
        
        # Payment method breakdown
        payment_methods = Sale.objects.filter(
            tenant=tenant,
            sale_date__date__gte=thirty_days_ago
        ).values('payment_method').annotate(
            count=Count('id'),
            total=Sum('total_amount')
        )
        
        # Customer type revenue breakdown
        customer_type_revenue = Sale.objects.filter(
            tenant=tenant,
            sale_date__date__gte=thirty_days_ago
        ).values('customer__customer_type').annotate(
            count=Count('id'),
            total=Sum('total_amount')
        )
        
        return Response({
            'overview': {
                'daily_sales': daily_sales,
                'monthly_sales': monthly_sales,
                'total_customers': total_customers,
                'recent_customers': recent_customers,
                'retail_customers': retail_customers,
                'wholesale_customers': wholesale_customers,
                'distributor_customers': distributor_customers,
                'total_products': total_products,
                'active_products': active_products,
                'total_warehouses': total_warehouses,
            },
            'inventory': {
                'low_stock_products': low_stock_products,
                'out_of_stock_products': out_of_stock_products,
                'total_stock_value': float(total_stock_value),
                'warehouse_summary': list(warehouse_inventory),
            },
            'profitability': {
                'total_revenue_30_days': total_revenue,
                'total_cost_30_days': total_cost,
                'profit_margin_30_days': profit_margin,
                'profit_percentage': round(profit_percentage, 2),
                'total_items_sold': recent_sales_items['item_count'] or 0,
            },
            'top_products': list(top_products),
            'top_customers': list(top_customers),
            'payment_methods': list(payment_methods),
            'customer_type_revenue': list(customer_type_revenue),
        })

# Check-in/Check-out Views
class StaffAttendanceCheckInView(APIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail')]
    
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
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail')]
    
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
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail')]

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
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail')]

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
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail')]

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
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail')]

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

# Bulk Operations for Retail
class RetailSaleBulkDeleteView(APIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail')]

    def post(self, request):
        sale_ids = request.data.get('ids', [])
        if not sale_ids:
            return Response({'error': 'No sale IDs provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        tenant = request.user.userprofile.tenant
        deleted_count = Sale.objects.filter(id__in=sale_ids, tenant=tenant).delete()[0]
        return Response({'message': f'{deleted_count} sale(s) deleted successfully'})


class RetailSaleBulkStatusUpdateView(APIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail')]

    def post(self, request):
        sale_ids = request.data.get('ids', [])
        new_status = request.data.get('payment_status')
        
        if not sale_ids:
            return Response({'error': 'No sale IDs provided'}, status=status.HTTP_400_BAD_REQUEST)
        if not new_status:
            return Response({'error': 'Payment status is required'}, status=status.HTTP_400_BAD_REQUEST)
        if new_status not in ['PENDING', 'PAID', 'PARTIAL']:
            return Response({'error': 'Invalid payment status'}, status=status.HTTP_400_BAD_REQUEST)
        
        tenant = request.user.userprofile.tenant
        updated_count = Sale.objects.filter(id__in=sale_ids, tenant=tenant).update(payment_status=new_status)
        return Response({'message': f'{updated_count} sale(s) updated successfully'})


class RetailPurchaseOrderBulkDeleteView(APIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail')]

    def post(self, request):
        po_ids = request.data.get('ids', [])
        if not po_ids:
            return Response({'error': 'No purchase order IDs provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        tenant = request.user.userprofile.tenant
        deleted_count = PurchaseOrder.objects.filter(id__in=po_ids, tenant=tenant).delete()[0]
        return Response({'message': f'{deleted_count} purchase order(s) deleted successfully'})


class RetailPurchaseOrderBulkStatusUpdateView(APIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail')]

    def post(self, request):
        po_ids = request.data.get('ids', [])
        new_status = request.data.get('status')
        
        if not po_ids:
            return Response({'error': 'No purchase order IDs provided'}, status=status.HTTP_400_BAD_REQUEST)
        if not new_status:
            return Response({'error': 'Status is required'}, status=status.HTTP_400_BAD_REQUEST)
        if new_status not in ['DRAFT', 'ORDERED', 'PARTIAL_RECEIVED', 'RECEIVED', 'CANCELLED']:
            return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
        
        tenant = request.user.userprofile.tenant
        updated_count = PurchaseOrder.objects.filter(id__in=po_ids, tenant=tenant).update(status=new_status)
        return Response({'message': f'{updated_count} purchase order(s) updated successfully'})


# Sale Return Views
class SaleReturnListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail')]
    serializer_class = SaleReturnSerializer
    
    def get_queryset(self):
        try:
            queryset = SaleReturn.objects.filter(tenant=self.request.user.userprofile.tenant).select_related(
                'sale', 'customer', 'processed_by__user'
            ).prefetch_related('items__product', 'items__inventory')
            return queryset
        except Exception:
            return SaleReturn.objects.none()
    
    def perform_create(self, serializer):
        from datetime import datetime
        from django.utils import timezone
        
        tenant = self.request.user.userprofile.tenant
        items_data = self.request.data.get('items', [])
        
        # Generate return number
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        return_number = f"RRET{timestamp}"
        
        # Calculate subtotal
        subtotal = sum(
            (item.get('quantity', 0) * item.get('unit_price', 0))
            for item in items_data
        )
        
        # Create the return
        sale_return = serializer.save(
            tenant=tenant,
            return_number=return_number,
            subtotal=subtotal,
            refund_amount=subtotal  # Default refund amount equals subtotal
        )
        
        # Create return items
        for item_data in items_data:
            sale_item_id = item_data.get('sale_item')
            product_id = item_data.get('product')
            inventory_id = item_data.get('inventory')
            quantity = item_data.get('quantity', 0)
            unit_price = item_data.get('unit_price', 0)
            reason = item_data.get('reason', '')
            
            if sale_item_id and product_id:
                try:
                    sale_item = SaleItem.objects.get(id=sale_item_id, tenant=tenant)
                    product = Product.objects.get(id=product_id, tenant=tenant)
                    
                    SaleReturnItem.objects.create(
                        sale_return=sale_return,
                        sale_item=sale_item,
                        product=product,
                        inventory=Inventory.objects.get(id=inventory_id, tenant=tenant) if inventory_id else None,
                        quantity=quantity,
                        unit_price=unit_price,
                        total_price=quantity * unit_price,
                        reason=reason,
                        tenant=tenant
                    )
                except (SaleItem.DoesNotExist, Product.DoesNotExist, Inventory.DoesNotExist):
                    pass  # Skip invalid items
        
        # Note: Stock is NOT restored here - only when return is processed

class SaleReturnDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail')]
    serializer_class = SaleReturnSerializer
    
    def get_queryset(self):
        try:
            return SaleReturn.objects.filter(tenant=self.request.user.userprofile.tenant)
        except Exception:
            return SaleReturn.objects.none()

class SaleReturnProcessView(APIView):
    """Process a return (approve and complete refund)"""
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('retail')]
    
    def post(self, request, pk):
        from django.utils import timezone
        try:
            tenant = request.user.userprofile.tenant
            sale_return = SaleReturn.objects.get(id=pk, tenant=tenant)
            
            if sale_return.status == 'PROCESSED':
                return Response({'error': 'Return already processed'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Update status
            sale_return.status = 'PROCESSED'
            sale_return.processed_by = request.user.userprofile
            sale_return.processed_at = timezone.now()
            sale_return.save()
            
            # Restore stock for all returned items
            for item in sale_return.items.all():
                inventory = item.inventory
                if inventory:
                    inventory.quantity_on_hand += item.quantity
                    inventory.quantity_available += item.quantity
                    inventory.save()
            
            return Response({'message': 'Return processed successfully', 'return': SaleReturnSerializer(sale_return).data})
        except SaleReturn.DoesNotExist:
            return Response({'error': 'Return not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST) 