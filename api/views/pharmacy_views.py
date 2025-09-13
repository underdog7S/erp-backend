from rest_framework import status, generics, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
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
from pharmacy.models import (
    MedicineCategory, Supplier, Medicine, MedicineBatch, Customer,
    Prescription, PrescriptionItem, Sale, SaleItem, PurchaseOrder,
    PurchaseOrderItem, StockAdjustment, StaffAttendance
)
from ..serializers import (
    MedicineCategorySerializer, PharmacySupplierSerializer as SupplierSerializer, MedicineSerializer,
    MedicineBatchSerializer, PharmacyCustomerSerializer as CustomerSerializer, PrescriptionSerializer,
    PrescriptionItemSerializer, PharmacySaleSerializer as SaleSerializer, PharmacySaleItemSerializer as SaleItemSerializer,
    PharmacyPurchaseOrderSerializer as PurchaseOrderSerializer, PharmacyPurchaseOrderItemSerializer as PurchaseOrderItemSerializer, PharmacyStockAdjustmentSerializer as StockAdjustmentSerializer,
    PharmacyStaffAttendanceSerializer as StaffAttendanceSerializer
)

# Medicine Category Views
class MedicineCategoryListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MedicineCategorySerializer
    
    def get_queryset(self):
        return MedicineCategory.objects.filter(tenant=self.request.user.userprofile.tenant)
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.userprofile.tenant)

class MedicineCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MedicineCategorySerializer
    
    def get_queryset(self):
        return MedicineCategory.objects.filter(tenant=self.request.user.userprofile.tenant)

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

# Medicine Views
class MedicineListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
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
    permission_classes = [IsAuthenticated]
    serializer_class = MedicineSerializer
    
    def get_queryset(self):
        return Medicine.objects.filter(tenant=self.request.user.userprofile.tenant)

# Medicine Search View for Barcode Scanning
class MedicineSearchView(APIView):
    permission_classes = [IsAuthenticated]
    
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
    permission_classes = [IsAuthenticated]
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
    permission_classes = [IsAuthenticated]
    serializer_class = MedicineBatchSerializer
    
    def get_queryset(self):
        return MedicineBatch.objects.filter(tenant=self.request.user.userprofile.tenant)

# Customer Views
class CustomerListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
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
    permission_classes = [IsAuthenticated]
    serializer_class = CustomerSerializer
    
    def get_queryset(self):
        return Customer.objects.filter(tenant=self.request.user.userprofile.tenant)

# Prescription Views
class PrescriptionListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
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
    permission_classes = [IsAuthenticated]
    serializer_class = PrescriptionSerializer
    
    def get_queryset(self):
        return Prescription.objects.filter(tenant=self.request.user.userprofile.tenant)

# Sale Views
class SaleListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SaleSerializer
    
    def get_queryset(self):
        try:
            queryset = Sale.objects.filter(tenant=self.request.user.userprofile.tenant).prefetch_related(
                'items__medicine_batch__medicine',
                'customer',
                'sold_by__user'
            )
            customer = self.request.query_params.get('customer', None)
            if customer:
                queryset = queryset.filter(customer_id=customer)
            return queryset
        except Exception as e:
            # If there's an error with tenant filtering, return empty queryset
            print(f"Error in SaleListCreateView.get_queryset: {e}")
            return Sale.objects.none()
    
    def perform_create(self, serializer):
        # Pass items data in context for the serializer to handle
        items_data = self.request.data.get('items', [])
        # Update the context with items data
        serializer._context.update({
            'items': items_data,
            'request': self.request
        })
        serializer.save(
            tenant=self.request.user.userprofile.tenant, 
            sold_by=self.request.user.userprofile
        )

class SaleDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SaleSerializer
    
    def get_queryset(self):
        try:
            return Sale.objects.filter(tenant=self.request.user.userprofile.tenant)
        except Exception as e:
            # If there's an error with tenant filtering, return empty queryset
            print(f"Error in SaleDetailView.get_queryset: {e}")
            return Sale.objects.none()

# Purchase Order Views
class PurchaseOrderListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PurchaseOrderSerializer
    
    def get_queryset(self):
        queryset = PurchaseOrder.objects.filter(tenant=self.request.user.userprofile.tenant)
        supplier = self.request.query_params.get('supplier', None)
        if supplier:
            queryset = queryset.filter(supplier_id=supplier)
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.userprofile.tenant, created_by=self.request.user.userprofile)

class PurchaseOrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PurchaseOrderSerializer
    
    def get_queryset(self):
        return PurchaseOrder.objects.filter(tenant=self.request.user.userprofile.tenant)

# Stock Adjustment Views
class StockAdjustmentListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = StockAdjustmentSerializer
    
    def get_queryset(self):
        return StockAdjustment.objects.filter(tenant=self.request.user.userprofile.tenant)
    
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
class PharmacyAnalyticsView(APIView):
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
        low_stock_medicines = MedicineBatch.objects.filter(
            tenant=tenant,
            quantity_available__lte=10
        ).count()
        
        expiring_medicines = MedicineBatch.objects.filter(
            tenant=tenant,
            expiry_date__lte=today + timedelta(days=30)
        ).count()
        
        # Customer analytics
        total_customers = Customer.objects.filter(tenant=tenant).count()
        
        # Medicine analytics
        total_medicines = Medicine.objects.filter(tenant=tenant).count()
        total_sales = Sale.objects.filter(tenant=tenant).count()
        total_sales_amount = Sale.objects.filter(tenant=tenant).aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        
        return Response({
            'daily_sales': daily_sales,
            'monthly_sales': monthly_sales,
            'low_stock_medicines': low_stock_medicines,
            'expiring_medicines': expiring_medicines,
            'total_customers': total_customers,
            'total_medicines': total_medicines,
            'total_sales': total_sales,
            'total_sales_amount': total_sales_amount,
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

class MedicineExportView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

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

class PharmacyInventoryExportView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

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