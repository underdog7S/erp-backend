from rest_framework import status, generics, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from api.models.permissions import HasFeaturePermissionFactory
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
import logging

logger = logging.getLogger(__name__)
from pharmacy.models import (
    MedicineCategory, Supplier, Medicine, MedicineBatch, Customer,
    Prescription, PrescriptionItem, Sale, SaleItem, PurchaseOrder,
    PurchaseOrderItem, StockAdjustment, StaffAttendance, SaleReturn, SaleReturnItem,
    LoyaltyReward, LoyaltyTransaction
)
from ..serializers import (
    MedicineCategorySerializer, PharmacySupplierSerializer as SupplierSerializer, MedicineSerializer,
    MedicineBatchSerializer, PharmacyCustomerSerializer as CustomerSerializer, PrescriptionSerializer,
    PrescriptionItemSerializer, PharmacySaleSerializer as SaleSerializer, PharmacySaleItemSerializer as SaleItemSerializer,
    PharmacyPurchaseOrderSerializer as PurchaseOrderSerializer, PharmacyPurchaseOrderItemSerializer as PurchaseOrderItemSerializer, PharmacyStockAdjustmentSerializer as StockAdjustmentSerializer,
    PharmacyStaffAttendanceSerializer as StaffAttendanceSerializer,
    PharmacySaleReturnSerializer as SaleReturnSerializer, PharmacySaleReturnItemSerializer as SaleReturnItemSerializer,
    PharmacyLoyaltyRewardSerializer as LoyaltyRewardSerializer, PharmacyLoyaltyTransactionSerializer as LoyaltyTransactionSerializer
)

# Medicine Category Views
class MedicineCategoryListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('pharmacy')]
    serializer_class = MedicineCategorySerializer
    
    def get_queryset(self):
        return MedicineCategory.objects.filter(tenant=self.request.user.userprofile.tenant)
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.userprofile.tenant)

class MedicineCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('pharmacy')]
    serializer_class = MedicineCategorySerializer
    
    def get_queryset(self):
        return MedicineCategory.objects.filter(tenant=self.request.user.userprofile.tenant)

# Supplier Views
class SupplierListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('pharmacy')]
    serializer_class = SupplierSerializer
    
    def get_queryset(self):
        return Supplier.objects.filter(tenant=self.request.user.userprofile.tenant)
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.userprofile.tenant)

class SupplierDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('pharmacy')]
    serializer_class = SupplierSerializer
    
    def get_queryset(self):
        return Supplier.objects.filter(tenant=self.request.user.userprofile.tenant)

# Medicine Views
class MedicineListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('pharmacy')]
    serializer_class = MedicineSerializer
    
    def get_queryset(self):
        queryset = Medicine.objects.filter(tenant=self.request.user.userprofile.tenant)
        category = self.request.query_params.get('category', None)
        search = self.request.query_params.get('search', None)
        barcode = self.request.query_params.get('barcode', None)
        
        if category:
            queryset = queryset.filter(category_id=category)
        
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(generic_name__icontains=search) |
                Q(manufacturer__icontains=search) |
                Q(description__icontains=search)
            )
        
        if barcode:
            queryset = queryset.filter(barcode=barcode)
            
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.userprofile.tenant)

class MedicineDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('pharmacy')]
    serializer_class = MedicineSerializer
    
    def get_queryset(self):
        return Medicine.objects.filter(tenant=self.request.user.userprofile.tenant)

# Medicine Search View for Barcode Scanning
class MedicineSearchView(APIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('pharmacy')]
    
    def get(self, request):
        try:
            tenant = request.user.userprofile.tenant
            barcode = request.query_params.get('barcode', None)
            search = request.query_params.get('search', None)
            
            print(f"API Debug: User: {request.user.username}")
            print(f"API Debug: Tenant: {tenant.name}")
            print(f"API Debug: Barcode: {barcode}")
            
            queryset = Medicine.objects.filter(tenant=tenant)
            print(f"API Debug: Total medicines for tenant: {queryset.count()}")
            
            if barcode:
                # Search by exact barcode match
                medicine = queryset.filter(barcode=barcode).first()
                print(f"API Debug: Found medicine: {medicine}")
                if medicine:
                    serializer = MedicineSerializer(medicine)
                    return Response({
                        'found': True,
                        'medicine': serializer.data
                    })
                else:
                    return Response({
                        'found': False,
                        'message': 'No medicine found with this barcode'
                    })
            
            elif search:
                # Search by name, generic name, or manufacturer
                medicines = queryset.filter(
                    Q(name__icontains=search) | 
                    Q(generic_name__icontains=search) |
                    Q(manufacturer__icontains=search) |
                    Q(barcode__icontains=search)
                )[:10]  # Limit to 10 results
                
                serializer = MedicineSerializer(medicines, many=True)
                return Response({
                    'found': len(medicines) > 0,
                    'medicines': serializer.data,
                    'count': len(medicines)
                })
            
            return Response({
                'error': 'Please provide either barcode or search parameter'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            print(f"API Error: {str(e)}")
            return Response({
                'error': 'An error occurred while processing the request'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Medicine Batch Views
class MedicineBatchListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('pharmacy')]
    serializer_class = MedicineBatchSerializer
    
    def get_queryset(self):
        queryset = MedicineBatch.objects.filter(tenant=self.request.user.userprofile.tenant)
        medicine = self.request.query_params.get('medicine', None)
        if medicine:
            queryset = queryset.filter(medicine_id=medicine)
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.userprofile.tenant)

class MedicineBatchDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('pharmacy')]
    serializer_class = MedicineBatchSerializer
    
    def get_queryset(self):
        return MedicineBatch.objects.filter(tenant=self.request.user.userprofile.tenant)

# Customer Views
class CustomerListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('pharmacy')]
    serializer_class = CustomerSerializer
    
    def get_queryset(self):
        queryset = Customer.objects.filter(tenant=self.request.user.userprofile.tenant)
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(phone__icontains=search) | 
                Q(email__icontains=search)
            )
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.userprofile.tenant)

class CustomerDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('pharmacy')]
    serializer_class = CustomerSerializer
    
    def get_queryset(self):
        return Customer.objects.filter(tenant=self.request.user.userprofile.tenant)

# Prescription Views
class PrescriptionListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('pharmacy')]
    serializer_class = PrescriptionSerializer
    
    def get_queryset(self):
        queryset = Prescription.objects.filter(tenant=self.request.user.userprofile.tenant)
        customer = self.request.query_params.get('customer', None)
        if customer:
            queryset = queryset.filter(customer_id=customer)
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.userprofile.tenant)

class PrescriptionDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('pharmacy')]
    serializer_class = PrescriptionSerializer
    
    def get_queryset(self):
        return Prescription.objects.filter(tenant=self.request.user.userprofile.tenant)

# Sale Views
class SaleListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('pharmacy')]
    serializer_class = SaleSerializer
    
    def get_queryset(self):
        try:
            queryset = Sale.objects.filter(tenant=self.request.user.userprofile.tenant).prefetch_related(
                'items__medicine_batch__medicine',
                'customer',
                'sold_by__user'
            )
            customer = self.request.query_params.get('customer', None)
            search = self.request.query_params.get('search', None)
            payment_method = self.request.query_params.get('payment_method', None)
            payment_status = self.request.query_params.get('payment_status', None)
            date_from = self.request.query_params.get('date_from', None)
            date_to = self.request.query_params.get('date_to', None)
            
            if customer:
                queryset = queryset.filter(customer_id=customer)
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
            if date_from:
                queryset = queryset.filter(sale_date__date__gte=date_from)
            if date_to:
                queryset = queryset.filter(sale_date__date__lte=date_to)
            
            return queryset.order_by('-sale_date')
        except Exception as e:
            # If there's an error with tenant filtering, return empty queryset
            logger.error(f"Error in SaleListCreateView.get_queryset: {e}", exc_info=True)
            return Sale.objects.none()
    
    def perform_create(self, serializer):
        # Pass items data in context for the serializer to handle
        items_data = self.request.data.get('items', [])
        # Update the context with items data
        serializer._context.update({
            'items': items_data,
            'request': self.request
        })
        sale = serializer.save(
            tenant=self.request.user.userprofile.tenant, 
            sold_by=self.request.user.userprofile
        )
        
        # Award loyalty points if customer is enrolled and sale is paid
        if sale.customer and sale.customer.loyalty_enrolled and sale.payment_status == 'PAID':
            points_per_rupee = 1  # Default: 1 point per rupee, can be made configurable
            points = sale.customer.calculate_loyalty_points(sale.total_amount, points_per_rupee)
            if points > 0:
                sale.customer.add_loyalty_points(
                    points, 
                    sale=sale, 
                    description=f"Points earned from sale {sale.invoice_number}"
                )

class SaleDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('pharmacy')]
    serializer_class = SaleSerializer
    
    def get_queryset(self):
        try:
            return Sale.objects.filter(tenant=self.request.user.userprofile.tenant).select_related(
                'customer', 'sold_by', 'sold_by__user', 'tenant'
            ).prefetch_related('items', 'items__medicine_batch', 'items__medicine_batch__medicine')
        except Exception as e:
            # If there's an error with tenant filtering, return empty queryset
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in SaleDetailView.get_queryset: {e}", exc_info=True)
            return Sale.objects.none()

# Purchase Order Views
class PurchaseOrderListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('pharmacy')]
    serializer_class = PurchaseOrderSerializer
    
    def get_queryset(self):
        queryset = PurchaseOrder.objects.filter(tenant=self.request.user.userprofile.tenant)
        supplier = self.request.query_params.get('supplier', None)
        status = self.request.query_params.get('status', None)
        search = self.request.query_params.get('search', None)
        date_from = self.request.query_params.get('date_from', None)
        date_to = self.request.query_params.get('date_to', None)
        
        if supplier:
            queryset = queryset.filter(supplier_id=supplier)
        if status:
            queryset = queryset.filter(status=status)
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
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('pharmacy')]
    serializer_class = PurchaseOrderSerializer
    
    def get_queryset(self):
        return PurchaseOrder.objects.filter(tenant=self.request.user.userprofile.tenant)

# Stock Adjustment Views
class StockAdjustmentListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('pharmacy')]
    serializer_class = StockAdjustmentSerializer
    
    def get_queryset(self):
        return StockAdjustment.objects.filter(tenant=self.request.user.userprofile.tenant)
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.userprofile.tenant, adjusted_by=self.request.user.userprofile)

class StockAdjustmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('pharmacy')]
    serializer_class = StockAdjustmentSerializer
    
    def get_queryset(self):
        return StockAdjustment.objects.filter(tenant=self.request.user.userprofile.tenant)

# Staff Attendance Views
class StaffAttendanceListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('pharmacy')]
    serializer_class = StaffAttendanceSerializer
    
    def get_queryset(self):
        return StaffAttendance.objects.filter(tenant=self.request.user.userprofile.tenant)
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.userprofile.tenant)

class StaffAttendanceDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('pharmacy')]
    serializer_class = StaffAttendanceSerializer
    
    def get_queryset(self):
        return StaffAttendance.objects.filter(tenant=self.request.user.userprofile.tenant)

# Analytics Views
class PharmacyAnalyticsView(APIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('pharmacy'), HasFeaturePermissionFactory('analytics')]
    
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
            total_cost=Sum(F('medicine_batch__cost_price') * F('quantity')),
            item_count=Count('id')
        )
        
        total_revenue = float(recent_sales_items['total_revenue'] or 0)
        total_cost = float(recent_sales_items['total_cost'] or 0)
        profit_margin = total_revenue - total_cost
        profit_percentage = (profit_margin / total_revenue * 100) if total_revenue > 0 else 0
        
        # Inventory analytics
        low_stock_medicines = MedicineBatch.objects.filter(
            tenant=tenant,
            quantity_available__lte=10
        ).count()
        
        expired_medicines = MedicineBatch.objects.filter(
            tenant=tenant,
            expiry_date__lt=today,
            quantity_available__gt=0
        ).count()
        
        expiring_soon_medicines = MedicineBatch.objects.filter(
            tenant=tenant,
            expiry_date__gte=today,
            expiry_date__lte=today + timedelta(days=30),
            quantity_available__gt=0
        ).count()
        
        # Top selling medicines (last 30 days)
        top_medicines = SaleItem.objects.filter(
            tenant=tenant,
            sale__sale_date__date__gte=thirty_days_ago
        ).values(
            'medicine_batch__medicine__name'
        ).annotate(
            total_quantity=Sum('quantity'),
            total_revenue=Sum('total_price')
        ).order_by('-total_revenue')[:10]
        
        # Customer analytics
        total_customers = Customer.objects.filter(tenant=tenant).count()
        recent_customers = Customer.objects.filter(
            tenant=tenant,
            created_at__date__gte=thirty_days_ago
        ).count()
        
        # Prescription analytics
        total_prescriptions = Prescription.objects.filter(tenant=tenant).count()
        recent_prescriptions = Prescription.objects.filter(
            tenant=tenant,
            prescription_date__gte=thirty_days_ago
        ).count()
        
        # Supplier analytics
        total_suppliers = Supplier.objects.filter(tenant=tenant).count()
        
        # Medicine analytics
        total_medicines = Medicine.objects.filter(tenant=tenant).count()
        
        # Stock value calculation
        total_stock_value = MedicineBatch.objects.filter(
            tenant=tenant,
            quantity_available__gt=0
        ).aggregate(
            total_value=Sum(F('cost_price') * F('quantity_available'))
        )['total_value'] or 0
        
        # Payment method breakdown
        payment_methods = Sale.objects.filter(
            tenant=tenant,
            sale_date__date__gte=thirty_days_ago
        ).values('payment_method').annotate(
            count=Count('id'),
            total=Sum('total_amount')
        )
        
        # Weekly revenue comparison (NEW)
        seven_days_ago = today - timedelta(days=7)
        this_week_revenue = Sale.objects.filter(
            tenant=tenant,
            sale_date__date__gte=seven_days_ago
        ).aggregate(total=Sum('total_amount'))
        last_week_revenue = Sale.objects.filter(
            tenant=tenant,
            sale_date__date__gte=seven_days_ago - timedelta(days=7),
            sale_date__date__lt=seven_days_ago
        ).aggregate(total=Sum('total_amount'))
        week_growth = ((float(this_week_revenue['total'] or 0) - float(last_week_revenue['total'] or 0)) / float(last_week_revenue['total'] or 1) * 100) if last_week_revenue['total'] else 0
        
        # Daily revenue trend (last 7 days) (NEW)
        daily_revenue = []
        for i in range(7):
            date = today - timedelta(days=i)
            day_revenue = Sale.objects.filter(
                tenant=tenant,
                sale_date__date=date
            ).aggregate(total=Sum('total_amount'))
            daily_revenue.append({
                'date': date.strftime('%Y-%m-%d'),
                'day': date.strftime('%a'),
               'revenue': float(day_revenue['total'] or 0),
                'transactions': Sale.objects.filter(tenant=tenant, sale_date__date=date).count()
            })
        daily_revenue.reverse()
        
        # Customer retention (NEW)
        repeat_customers = Sale.objects.filter(
            tenant=tenant,
            sale_date__date__gte=thirty_days_ago
        ).exclude(customer__isnull=True).values('customer__id').annotate(
            purchase_count=Count('id')
        ).filter(purchase_count__gt=1).count()
        
        return Response({
            'overview': {
                'daily_sales': daily_sales,
                'monthly_sales': monthly_sales,
                'total_customers': total_customers,
                'recent_customers': recent_customers,
                'total_medicines': total_medicines,
                'total_suppliers': total_suppliers,
                'total_prescriptions': total_prescriptions,
                'recent_prescriptions': recent_prescriptions,
            },
            'inventory': {
                'low_stock_medicines': low_stock_medicines,
                'expired_medicines': expired_medicines,
                'expiring_soon_medicines': expiring_soon_medicines,
                'total_stock_value': float(total_stock_value),
            },
            'profitability': {
                'total_revenue_30_days': total_revenue,
                'total_cost_30_days': total_cost,
                'profit_margin_30_days': profit_margin,
                'profit_percentage': round(profit_percentage, 2),
                'total_items_sold': recent_sales_items['item_count'] or 0,
            },
            'revenue': {
                'this_week': float(this_week_revenue['total'] or 0),
                'last_week': float(last_week_revenue['total'] or 0),
                'week_growth_percent': round(week_growth, 2),
            },
            'daily_trends': daily_revenue,
            'top_medicines': list(top_medicines),
            'payment_methods': list(payment_methods),
            'customers': {
                'repeat_customers_30_days': repeat_customers,
            },
        })

# Check-in/Check-out Views
class StaffAttendanceCheckInView(APIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('pharmacy')]
    
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
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('pharmacy')]
    
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

class MedicineExportView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('pharmacy')]

    def get(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        medicines = Medicine._default_manager.filter(tenant=profile.tenant)
        
        # Filtering
        category_id = request.query_params.get('category')
        search = request.query_params.get('search')
        manufacturer = request.query_params.get('manufacturer')
        
        if category_id:
            medicines = medicines.filter(category_id=category_id)
        if search:
            medicines = medicines.filter(
                Q(name__icontains=search) | 
                Q(generic_name__icontains=search) |
                Q(manufacturer__icontains=search)
            )
        if manufacturer:
            medicines = medicines.filter(manufacturer__icontains=manufacturer)
        
        export_format = request.query_params.get('format', 'csv').lower()
        
        if export_format == 'pdf':
            try:
                buffer = BytesIO()
                p = canvas.Canvas(buffer, pagesize=letter)
                width, height = letter
                y = height - 40
                p.setFont("Helvetica-Bold", 14)
                p.drawString(40, y, "Medicine Inventory Report")
                y -= 30
                p.setFont("Helvetica", 8)
                headers = ["ID", "Name", "Generic", "Category", "Manufacturer", "Price", "Stock"]
                for i, h in enumerate(headers):
                    p.drawString(40 + i*70, y, h)
                y -= 20
                
                for med in medicines:
                    # Calculate current stock
                    total_stock = MedicineBatch._default_manager.filter(
                        medicine=med, 
                        tenant=profile.tenant,
                        expiry_date__gte=timezone.now().date()
                    ).aggregate(total=Sum('current_stock'))['total'] or 0
                    
                    row = [
                        str(med.id),
                        med.name,
                        med.generic_name or "N/A",
                        med.category.name if med.category else "N/A",
                        med.manufacturer or "N/A",
                        f"₹{med.price}",
                        str(total_stock)
                    ]
                    for i, val in enumerate(row):
                        p.drawString(40 + i*70, y, val)
                    y -= 15
                    if y < 40:
                        p.showPage()
                        y = height - 40
                p.save()
                buffer.seek(0)
                response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename="medicines.pdf"'
                return response
            except Exception as e:
                return Response({'error': f'PDF export failed: {str(e)}'}, status=500)
        else:
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="medicines.csv"'
            writer = csv.writer(response)
            writer.writerow(["ID", "Name", "Generic Name", "Category", "Manufacturer", "Description", "Price", "Barcode", "Prescription Required"])
            
            for med in medicines:
                # Calculate current stock
                total_stock = MedicineBatch._default_manager.filter(
                    medicine=med, 
                    tenant=profile.tenant,
                    expiry_date__gte=timezone.now().date()
                ).aggregate(total=Sum('current_stock'))['total'] or 0
                
                writer.writerow([
                    med.id,
                    med.name,
                    med.generic_name or "",
                    med.category.name if med.category else "",
                    med.manufacturer or "",
                    med.description or "",
                    med.price,
                    med.barcode or "",
                    "Yes" if med.prescription_required else "No"
                ])
            return response

class PharmacySaleExportView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('pharmacy')]

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
                p.drawString(40, y, "Pharmacy Sales Report")
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
                response['Content-Disposition'] = 'attachment; filename="pharmacy_sales.pdf"'
                return response
            except Exception as e:
                return Response({'error': f'PDF export failed: {str(e)}'}, status=500)
        else:
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="pharmacy_sales.csv"'
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

class PharmacyPurchaseOrderExportView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('pharmacy')]

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

class PharmacyInventoryExportView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('pharmacy')]

    def get(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        batches = MedicineBatch._default_manager.filter(tenant=profile.tenant)
        
        # Filtering
        medicine_id = request.query_params.get('medicine')
        supplier_id = request.query_params.get('supplier')
        expiry_status = request.query_params.get('expiry_status')  # expired, expiring_soon, valid
        
        if medicine_id:
            batches = batches.filter(medicine_id=medicine_id)
        if supplier_id:
            batches = batches.filter(supplier_id=supplier_id)
        if expiry_status:
            today = timezone.now().date()
            if expiry_status == 'expired':
                batches = batches.filter(expiry_date__lt=today)
            elif expiry_status == 'expiring_soon':
                thirty_days_from_now = today + timedelta(days=30)
                batches = batches.filter(expiry_date__gte=today, expiry_date__lte=thirty_days_from_now)
            elif expiry_status == 'valid':
                batches = batches.filter(expiry_date__gt=today)
        
        export_format = request.query_params.get('format', 'csv').lower()
        
        if export_format == 'pdf':
            try:
                buffer = BytesIO()
                p = canvas.Canvas(buffer, pagesize=letter)
                width, height = letter
                y = height - 40
                p.setFont("Helvetica-Bold", 14)
                p.drawString(40, y, "Pharmacy Inventory Report")
                y -= 30
                p.setFont("Helvetica", 8)
                headers = ["Medicine", "Batch", "Supplier", "Stock", "Expiry", "Cost"]
                for i, h in enumerate(headers):
                    p.drawString(40 + i*80, y, h)
                y -= 20
                
                for batch in batches:
                    row = [
                        batch.medicine.name,
                        batch.batch_number,
                        batch.supplier.name if batch.supplier else "N/A",
                        str(batch.current_stock),
                        batch.expiry_date.strftime('%Y-%m-%d'),
                        f"₹{batch.cost_price}"
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
                response['Content-Disposition'] = 'attachment; filename="pharmacy_inventory.pdf"'
                return response
            except Exception as e:
                return Response({'error': f'PDF export failed: {str(e)}'}, status=500)
        else:
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="pharmacy_inventory.csv"'
            writer = csv.writer(response)
            writer.writerow(["Medicine", "Batch Number", "Supplier", "Manufacturing Date", "Expiry Date", "Cost Price", "Selling Price", "Current Stock", "Initial Stock"])
            
            for batch in batches:
                writer.writerow([
                    batch.medicine.name,
                    batch.batch_number,
                    batch.supplier.name if batch.supplier else "N/A",
                    batch.manufacturing_date.strftime('%Y-%m-%d') if batch.manufacturing_date else "",
                    batch.expiry_date.strftime('%Y-%m-%d'),
                    batch.cost_price,
                    batch.selling_price,
                    batch.current_stock,
                    batch.initial_stock
                ])
            return response

# Bulk Operations for Pharmacy
class PharmacySaleBulkDeleteView(APIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('pharmacy')]

    def post(self, request):
        sale_ids = request.data.get('ids', [])
        if not sale_ids:
            return Response({'error': 'No sale IDs provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        tenant = request.user.userprofile.tenant
        deleted_count = Sale.objects.filter(id__in=sale_ids, tenant=tenant).delete()[0]
        return Response({'message': f'{deleted_count} sale(s) deleted successfully'})


class PharmacySaleBulkStatusUpdateView(APIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('pharmacy')]

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


class PharmacyPurchaseOrderBulkDeleteView(APIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('pharmacy')]

    def post(self, request):
        po_ids = request.data.get('ids', [])
        if not po_ids:
            return Response({'error': 'No purchase order IDs provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        tenant = request.user.userprofile.tenant
        deleted_count = PurchaseOrder.objects.filter(id__in=po_ids, tenant=tenant).delete()[0]
        return Response({'message': f'{deleted_count} purchase order(s) deleted successfully'})


class PharmacyPurchaseOrderBulkStatusUpdateView(APIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('pharmacy')]

    def post(self, request):
        po_ids = request.data.get('ids', [])
        new_status = request.data.get('status')
        
        if not po_ids:
            return Response({'error': 'No purchase order IDs provided'}, status=status.HTTP_400_BAD_REQUEST)
        if not new_status:
            return Response({'error': 'Status is required'}, status=status.HTTP_400_BAD_REQUEST)
        if new_status not in ['DRAFT', 'ORDERED', 'RECEIVED', 'CANCELLED']:
            return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
        
        tenant = request.user.userprofile.tenant
        updated_count = PurchaseOrder.objects.filter(id__in=po_ids, tenant=tenant).update(status=new_status)
        return Response({'message': f'{updated_count} purchase order(s) updated successfully'})


# Sale Return Views
class SaleReturnListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('pharmacy')]
    serializer_class = SaleReturnSerializer
    
    def get_queryset(self):
        try:
            queryset = SaleReturn.objects.filter(tenant=self.request.user.userprofile.tenant).select_related(
                'sale', 'customer', 'processed_by__user'
            ).prefetch_related('items__medicine_batch__medicine')
            
            # Filtering options
            sale_id = self.request.query_params.get('sale', None)
            customer_id = self.request.query_params.get('customer', None)
            status = self.request.query_params.get('status', None)
            return_type = self.request.query_params.get('return_type', None)
            search = self.request.query_params.get('search', None)
            date_from = self.request.query_params.get('date_from', None)
            date_to = self.request.query_params.get('date_to', None)
            
            if sale_id:
                queryset = queryset.filter(sale_id=sale_id)
            if customer_id:
                queryset = queryset.filter(customer_id=customer_id)
            if status:
                queryset = queryset.filter(status=status)
            if return_type:
                queryset = queryset.filter(return_type=return_type)
            if search:
                queryset = queryset.filter(
                    Q(return_number__icontains=search) |
                    Q(sale__invoice_number__icontains=search) |
                    Q(customer__name__icontains=search)
                )
            if date_from:
                queryset = queryset.filter(return_date__gte=date_from)
            if date_to:
                queryset = queryset.filter(return_date__lte=date_to)
            
            return queryset.order_by('-return_date')
        except Exception as e:
            return SaleReturn.objects.none()
    
    def perform_create(self, serializer):
        tenant = self.request.user.userprofile.tenant
        items_data = self.request.data.get('items', [])
        
        # Generate return number
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        return_number = f"RET{timestamp}"
        
        # Calculate totals
        subtotal = 0
        for item_data in items_data:
            quantity = item_data.get('quantity', 0)
            unit_price = item_data.get('unit_price', 0)
            subtotal += quantity * unit_price
        
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
            medicine_batch_id = item_data.get('medicine_batch')
            quantity = item_data.get('quantity', 0)
            unit_price = item_data.get('unit_price', 0)
            reason = item_data.get('reason', '')
            
            if sale_item_id and medicine_batch_id:
                try:
                    from pharmacy.models import SaleItem, MedicineBatch
                    sale_item = SaleItem.objects.get(id=sale_item_id, tenant=tenant)
                    medicine_batch = MedicineBatch.objects.get(id=medicine_batch_id, tenant=tenant)
                    
                    SaleReturnItem.objects.create(
                        sale_return=sale_return,
                        sale_item=sale_item,
                        medicine_batch=medicine_batch,
                        quantity=quantity,
                        unit_price=unit_price,
                        total_price=quantity * unit_price,
                        reason=reason,
                        tenant=tenant
                    )
                except (SaleItem.DoesNotExist, MedicineBatch.DoesNotExist):
                    pass  # Skip invalid items
        
        # Note: Stock is NOT restored here - only when return is processed

class SaleReturnDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('pharmacy')]
    serializer_class = SaleReturnSerializer
    
    def get_queryset(self):
        try:
            return SaleReturn.objects.filter(tenant=self.request.user.userprofile.tenant)
        except Exception:
            return SaleReturn.objects.none()

class SaleReturnProcessView(APIView):
    """Process a return (approve and complete refund)"""
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('pharmacy')]
    
    def post(self, request, pk):
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
                batch = item.medicine_batch
                if batch:
                    batch.quantity_available += item.quantity
                    batch.save()
            
            return Response({'message': 'Return processed successfully', 'return': SaleReturnSerializer(sale_return).data})
        except SaleReturn.DoesNotExist:
            return Response({'error': 'Return not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

# Loyalty Program Views
class LoyaltyRewardListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('pharmacy')]
    serializer_class = LoyaltyRewardSerializer
    
    def get_queryset(self):
        queryset = LoyaltyReward.objects.filter(tenant=self.request.user.userprofile.tenant)
        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.userprofile.tenant)

class LoyaltyRewardDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('pharmacy')]
    serializer_class = LoyaltyRewardSerializer
    
    def get_queryset(self):
        return LoyaltyReward.objects.filter(tenant=self.request.user.userprofile.tenant)

class LoyaltyTransactionListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('pharmacy')]
    serializer_class = LoyaltyTransactionSerializer
    
    def get_queryset(self):
        queryset = LoyaltyTransaction.objects.filter(tenant=self.request.user.userprofile.tenant)
        customer = self.request.query_params.get('customer', None)
        transaction_type = self.request.query_params.get('transaction_type', None)
        if customer:
            queryset = queryset.filter(customer_id=customer)
        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)
        return queryset.order_by('-transaction_date')
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.userprofile.tenant, created_by=self.request.user.userprofile)

class LoyaltyTransactionDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('pharmacy')]
    serializer_class = LoyaltyTransactionSerializer
    
    def get_queryset(self):
        return LoyaltyTransaction.objects.filter(tenant=self.request.user.userprofile.tenant)

class LoyaltyRedeemView(APIView):
    """Redeem loyalty points for a reward"""
    permission_classes = [IsAuthenticated, HasFeaturePermissionFactory('pharmacy')]
    
    def post(self, request):
        try:
            tenant = request.user.userprofile.tenant
            customer_id = request.data.get('customer_id')
            reward_id = request.data.get('reward_id')
            
            if not customer_id or not reward_id:
                return Response({'error': 'customer_id and reward_id are required'}, status=status.HTTP_400_BAD_REQUEST)
            
            customer = Customer.objects.get(id=customer_id, tenant=tenant)
            reward = LoyaltyReward.objects.get(id=reward_id, tenant=tenant, is_active=True)
            
            if not customer.loyalty_enrolled:
                return Response({'error': 'Customer is not enrolled in loyalty program'}, status=status.HTTP_400_BAD_REQUEST)
            
            if customer.loyalty_points < reward.points_required:
                return Response({'error': 'Insufficient loyalty points'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if reward is valid (date range)
            today = timezone.now().date()
            if reward.valid_from and reward.valid_from > today:
                return Response({'error': 'Reward is not yet valid'}, status=status.HTTP_400_BAD_REQUEST)
            if reward.valid_until and reward.valid_until < today:
                return Response({'error': 'Reward has expired'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Redeem points
            customer.redeem_loyalty_points(
                reward.points_required,
                reward=reward,
                description=f"Redeemed reward: {reward.name}"
            )
            
            return Response({
                'message': 'Points redeemed successfully',
                'customer': CustomerSerializer(customer).data,
                'reward': LoyaltyRewardSerializer(reward).data
            })
        except Customer.DoesNotExist:
            return Response({'error': 'Customer not found'}, status=status.HTTP_404_NOT_FOUND)
        except LoyaltyReward.DoesNotExist:
            return Response({'error': 'Reward not found or inactive'}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST) 