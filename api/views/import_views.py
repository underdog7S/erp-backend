import os
import csv
import json
import tempfile
from datetime import datetime
from decimal import Decimal
from django.http import HttpResponse, JsonResponse
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from api.models.user import UserProfile
from pharmacy.models import Medicine, MedicineCategory, Customer
from retail.models import Product, ProductCategory, Customer as RetailCustomer
from api.serializers import MedicineSerializer, ProductSerializer

class MedicineImportView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Import medicines from CSV/Excel file"""
        try:
            # Check if user has pharmacy permissions
            user_profile = UserProfile.objects.get(user=request.user)
            if user_profile.role.name not in ['admin', 'pharmacy_admin', 'pharmacist']:
                return Response({'error': 'Pharmacy access required'}, status=status.HTTP_403_FORBIDDEN)
            
            # Check if file was uploaded
            if 'file' not in request.FILES:
                return Response({'error': 'No file uploaded'}, status=status.HTTP_400_BAD_REQUEST)
            
            uploaded_file = request.FILES['file']
            tenant = user_profile.tenant
            
            # Validate file type
            file_extension = uploaded_file.name.split('.')[-1].lower()
            if file_extension not in ['csv', 'xls', 'xlsx']:
                return Response({'error': 'Only CSV, XLS, and XLSX files are supported'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Process CSV file
            if file_extension == 'csv':
                return self.process_csv_medicines(uploaded_file, tenant)
            else:
                return self.process_excel_medicines(uploaded_file, tenant)
                
        except Exception as e:
            import traceback
            print(f"Medicine import error: {str(e)}")
            print(traceback.format_exc())
            return Response({'error': f'Import failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def process_csv_medicines(self, uploaded_file, tenant):
        """Process CSV file for medicine import"""
        try:
            # Read CSV file
            decoded_file = uploaded_file.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded_file)
            
            imported_count = 0
            errors = []
            preview_data = []
            
            for row_num, row in enumerate(reader, start=2):  # Start from 2 to account for header
                try:
                    # Validate required fields
                    if not row.get('name'):
                        errors.append(f"Row {row_num}: Medicine name is required")
                        continue
                    
                    # Get or create category
                    category_name = row.get('category', 'General')
                    category, created = MedicineCategory.objects.get_or_create(
                        name=category_name,
                        tenant=tenant,
                        defaults={'description': f'Category for {category_name}'}
                    )
                    
                    # Create medicine
                    medicine_data = {
                        'name': row.get('name'),
                        'generic_name': row.get('generic_name', ''),
                        'category': category,
                        'manufacturer': row.get('manufacturer', ''),
                        'strength': row.get('strength', ''),
                        'dosage_form': row.get('dosage_form', 'TABLET'),
                        'prescription_required': row.get('prescription_required', 'false').lower() == 'true',
                        'description': row.get('description', ''),
                        'side_effects': row.get('side_effects', ''),
                        'storage_conditions': row.get('storage_conditions', ''),
                        'expiry_alert_days': int(row.get('expiry_alert_days', 30)),
                        'barcode': row.get('barcode', ''),
                        'tenant': tenant
                    }
                    
                    # Check if medicine already exists
                    existing_medicine = Medicine.objects.filter(
                        name=medicine_data['name'],
                        manufacturer=medicine_data['manufacturer'],
                        tenant=tenant
                    ).first()
                    
                    if existing_medicine:
                        errors.append(f"Row {row_num}: Medicine '{medicine_data['name']}' already exists")
                        continue
                    
                    # Create medicine
                    medicine = Medicine.objects.create(**medicine_data)
                    imported_count += 1
                    
                    # Add to preview
                    preview_data.append({
                        'name': medicine.name,
                        'generic_name': medicine.generic_name,
                        'category': medicine.category.name,
                        'manufacturer': medicine.manufacturer,
                        'strength': medicine.strength,
                        'dosage_form': medicine.dosage_form,
                        'prescription_required': medicine.prescription_required
                    })
                    
                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")
            
            return Response({
                'message': f'Successfully imported {imported_count} medicines',
                'imported_count': imported_count,
                'errors': errors,
                'preview_data': preview_data[:10]  # Show first 10 items
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({'error': f'CSV processing failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def process_excel_medicines(self, uploaded_file, tenant):
        """Process Excel file for medicine import"""
        # For now, return a message that Excel support is coming soon
        return Response({
            'message': 'Excel import support is coming soon. Please use CSV format for now.',
            'supported_formats': ['CSV']
        }, status=status.HTTP_200_OK)

class ProductImportView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Import products from CSV/Excel file"""
        try:
            # Check if user has retail permissions
            user_profile = UserProfile.objects.get(user=request.user)
            if user_profile.role.name not in ['admin', 'retail_admin', 'retail_manager']:
                return Response({'error': 'Retail access required'}, status=status.HTTP_403_FORBIDDEN)
            
            # Check if file was uploaded
            if 'file' not in request.FILES:
                return Response({'error': 'No file uploaded'}, status=status.HTTP_400_BAD_REQUEST)
            
            uploaded_file = request.FILES['file']
            tenant = user_profile.tenant
            
            # Validate file type
            file_extension = uploaded_file.name.split('.')[-1].lower()
            if file_extension not in ['csv', 'xls', 'xlsx']:
                return Response({'error': 'Only CSV, XLS, and XLSX files are supported'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Process CSV file
            if file_extension == 'csv':
                return self.process_csv_products(uploaded_file, tenant)
            else:
                return self.process_excel_products(uploaded_file, tenant)
                
        except Exception as e:
            import traceback
            print(f"Product import error: {str(e)}")
            print(traceback.format_exc())
            return Response({'error': f'Import failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def process_csv_products(self, uploaded_file, tenant):
        """Process CSV file for product import"""
        try:
            # Read CSV file
            decoded_file = uploaded_file.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded_file)
            
            imported_count = 0
            errors = []
            preview_data = []
            
            for row_num, row in enumerate(reader, start=2):  # Start from 2 to account for header
                try:
                    # Validate required fields
                    if not row.get('name'):
                        errors.append(f"Row {row_num}: Product name is required")
                        continue
                    
                    # Get or create category
                    category_name = row.get('category', 'General')
                    category, created = ProductCategory.objects.get_or_create(
                        name=category_name,
                        tenant=tenant,
                        defaults={'description': f'Category for {category_name}'}
                    )
                    
                    # Create product
                    product_data = {
                        'name': row.get('name'),
                        'description': row.get('description', ''),
                        'category': category,
                        'manufacturer': row.get('manufacturer', ''),
                        'sku': row.get('sku', ''),
                        'barcode': row.get('barcode', ''),
                        'unit_price': Decimal(row.get('unit_price', '0.00')),
                        'cost_price': Decimal(row.get('cost_price', '0.00')),
                        'reorder_level': int(row.get('reorder_level', 0)),
                        'current_stock': int(row.get('current_stock', 0)),
                        'location': row.get('location', ''),
                        'tenant': tenant
                    }
                    
                    # Check if product already exists
                    existing_product = Product.objects.filter(
                        name=product_data['name'],
                        sku=product_data['sku'],
                        tenant=tenant
                    ).first()
                    
                    if existing_product:
                        errors.append(f"Row {row_num}: Product '{product_data['name']}' already exists")
                        continue
                    
                    # Create product
                    product = Product.objects.create(**product_data)
                    imported_count += 1
                    
                    # Add to preview
                    preview_data.append({
                        'name': product.name,
                        'description': product.description,
                        'category': product.category.name,
                        'manufacturer': product.manufacturer,
                        'sku': product.sku,
                        'unit_price': float(product.unit_price),
                        'current_stock': product.current_stock
                    })
                    
                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")
            
            return Response({
                'message': f'Successfully imported {imported_count} products',
                'imported_count': imported_count,
                'errors': errors,
                'preview_data': preview_data[:10]  # Show first 10 items
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({'error': f'CSV processing failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def process_excel_products(self, uploaded_file, tenant):
        """Process Excel file for product import"""
        # For now, return a message that Excel support is coming soon
        return Response({
            'message': 'Excel import support is coming soon. Please use CSV format for now.',
            'supported_formats': ['CSV']
        }, status=status.HTTP_200_OK)

class ImportTemplateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Download import templates"""
        template_type = request.query_params.get('type', 'medicine')
        
        if template_type == 'medicine':
            return self.get_medicine_template()
        elif template_type == 'product':
            return self.get_product_template()
        else:
            return Response({'error': 'Invalid template type'}, status=status.HTTP_400_BAD_REQUEST)
    
    def get_medicine_template(self):
        """Generate medicine import template"""
        csv_content = """name,generic_name,category,manufacturer,strength,dosage_form,prescription_required,description,side_effects,storage_conditions,expiry_alert_days,barcode
Paracetamol 500mg,Acetaminophen,Pain Relief,ABC Pharmaceuticals,500mg,TABLET,false,Used for fever and pain relief,Rare side effects include nausea,Store in a cool dry place,30,
Amoxicillin 250mg,Amoxicillin,Antibiotic,XYZ Pharma,250mg,CAPSULE,true,Broad spectrum antibiotic,May cause stomach upset,Store in refrigerator,30,
Omeprazole 20mg,Omeprazole,Antacid,DEF Pharmaceuticals,20mg,CAPSULE,false,For acid reflux and ulcers,May cause headache,Store at room temperature,30,"""
        
        response = HttpResponse(csv_content, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="medicine_import_template.csv"'
        return response
    
    def get_product_template(self):
        """Generate product import template"""
        csv_content = """name,description,category,manufacturer,sku,barcode,unit_price,cost_price,reorder_level,current_stock,location
Laptop HP 15,High performance laptop,Electronics,HP,HP15-001,123456789012,45000.00,40000.00,5,10,Warehouse A
iPhone 15 Pro,Latest smartphone,Electronics,Apple,IP15P-001,987654321098,120000.00,110000.00,3,8,Warehouse B
Samsung TV 55",4K Smart TV,Electronics,Samsung,SS55-001,456789123456,65000.00,60000.00,2,5,Warehouse A"""
        
        response = HttpResponse(csv_content, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="product_import_template.csv"'
        return response 