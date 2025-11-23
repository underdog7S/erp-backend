import os
import json
import zipfile
import tempfile
from datetime import datetime
from decimal import Decimal
from django.http import HttpResponse
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import serializers
from api.models.user import UserProfile, Tenant, Role
from api.models.plan import Plan
from education.models import Student, Class, FeeStructure, FeePayment, Attendance, ReportCard, Department
from pharmacy.models import Medicine, MedicineBatch, Customer, Sale, SaleItem, Prescription
from retail.models import Product, Customer as RetailCustomer, Sale as RetailSale, SaleItem as RetailSaleItem, Supplier, Warehouse, Inventory
from api.views.users_views import UserProfileSerializer
from api.serializers import MedicineSerializer, PharmacyCustomerSerializer, PharmacySaleSerializer, ProductSerializer, RetailCustomerSerializer, RetailSaleSerializer
from api.models.serializers_education import StudentSerializer, ClassSerializer, FeeStructureSerializer, FeePaymentSerializer
from django.utils.text import slugify
import secrets

# Custom JSON encoder to handle Decimal and other non-serializable types
class DecimalEncoder(json.JSONEncoder):
	def default(self, obj):
		if isinstance(obj, Decimal):
			return float(obj)
		return super().default(obj)

# Simple serializers for admin export
class TenantSerializer(serializers.ModelSerializer):
	logo_url = serializers.SerializerMethodField()
	
	class Meta:
		model = Tenant
		fields = ['id', 'name', 'industry', 'created_at', 'plan', 'storage_used_mb', 'has_hotel', 'has_restaurant', 'has_salon', 'logo', 'logo_url']
	
	def get_logo_url(self, obj):
		if obj.logo:
			request = self.context.get('request')
			if request:
				return request.build_absolute_uri(obj.logo.url)
			return obj.logo.url
		return None

class RoleSerializer(serializers.ModelSerializer):
	class Meta:
		model = Role
		fields = ['id', 'name', 'description']

class AdminExportDataView(APIView):
	authentication_classes = [JWTAuthentication]
	permission_classes = [IsAuthenticated]
	
	def get(self, request):
		"""Export all system data as a ZIP file"""
		try:
			# Check if user is admin
			try:
				user_profile = UserProfile.objects.get(user=request.user)
			except UserProfile.DoesNotExist:
				return Response({'error': 'User profile not found'}, status=status.HTTP_404_NOT_FOUND)
			
			if not user_profile.role or user_profile.role.name != 'admin':
				return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
			
			if not user_profile.tenant:
				return Response({'error': 'Tenant not found for user'}, status=status.HTTP_404_NOT_FOUND)
			
			tenant = user_profile.tenant
			
			# Create temporary directory for export
			with tempfile.TemporaryDirectory() as temp_dir:
				export_data = {
					'export_info': {
						'export_date': datetime.now().isoformat(),
						'exported_by': request.user.username,
						'version': '1.0',
						'tenant': tenant.name
					},
					'system_data': {},
					'module_data': {}
				}
				
				# Export User Data (filtered by tenant)
				users = UserProfile.objects.filter(tenant=tenant)
				export_data['system_data']['users'] = UserProfileSerializer(users, many=True).data
				
				# Export Tenant Data (only current tenant)
				export_data['system_data']['tenant'] = TenantSerializer(tenant).data
				
				# Export Role Data (all roles)
				roles = Role.objects.all()
				export_data['system_data']['roles'] = RoleSerializer(roles, many=True).data
				
				# Export Plan Data (all plans)
				plans = Plan.objects.all()
				export_data['system_data']['plans'] = [
					{
						'id': plan.id,
						'name': plan.name,
						'description': plan.description,
						'price': float(plan.price) if plan.price else None,
						'billing_cycle': plan.billing_cycle,
						'monthly_equivalent': float(plan.monthly_equivalent) if plan.monthly_equivalent else None,
						'max_users': plan.max_users,
						'storage_limit_mb': plan.storage_limit_mb,
						'color': plan.color,
						'popular': plan.popular,
						'savings_text': plan.savings_text,
						'features': {
							'has_inventory': plan.has_inventory,
							'has_education': plan.has_education,
							'has_pharmacy': plan.has_pharmacy,
							'has_retail': plan.has_retail,
							'has_hotel': plan.has_hotel,
							'has_restaurant': plan.has_restaurant,
							'has_salon': plan.has_salon,
							'has_healthcare': plan.has_healthcare,
							'has_dashboard': plan.has_dashboard,
							'has_analytics': plan.has_analytics,
							'has_qc': plan.has_qc,
							'has_billing': plan.has_billing,
							'has_api_access': plan.has_api_access,
							'has_audit_logs': plan.has_audit_logs,
							'has_priority_support': plan.has_priority_support,
							'has_phone_support': plan.has_phone_support,
							'has_white_label': plan.has_white_label,
							'has_onboarding': plan.has_onboarding,
							'has_sla_support': plan.has_sla_support,
							'has_daily_backups': plan.has_daily_backups,
							'has_strategy_call': plan.has_strategy_call,
							'has_custom_reports': plan.has_custom_reports,
							'has_future_discount': plan.has_future_discount,
							'has_new_features_access': plan.has_new_features_access,
						}
					} for plan in plans
				]
				
				# Export Education Module Data (filtered by tenant)
				education_data = {}
				education_data['students'] = StudentSerializer(Student.objects.filter(tenant=tenant), many=True).data
				education_data['classes'] = ClassSerializer(Class.objects.filter(tenant=tenant), many=True).data
				education_data['fee_structures'] = FeeStructureSerializer(FeeStructure.objects.filter(tenant=tenant), many=True).data
				education_data['fee_payments'] = FeePaymentSerializer(FeePayment.objects.filter(tenant=tenant), many=True).data
				education_data['attendance'] = [
					{
						'id': att.id,
						'student': att.student.id,
						'date': att.date.isoformat(),
						'status': att.status,
						'tenant': att.tenant.id
					} for att in Attendance.objects.filter(tenant=tenant)
				]
				export_data['module_data']['education'] = education_data
				
				# Export Pharmacy Module Data (filtered by tenant)
				pharmacy_data = {}
				pharmacy_data['medicines'] = MedicineSerializer(Medicine.objects.filter(tenant=tenant), many=True).data
				pharmacy_data['customers'] = PharmacyCustomerSerializer(Customer.objects.filter(tenant=tenant), many=True).data
				pharmacy_data['sales'] = PharmacySaleSerializer(Sale.objects.filter(tenant=tenant), many=True).data
				pharmacy_data['prescriptions'] = [
					{
						'id': pres.id,
						'customer': pres.customer.id,
						'doctor_name': pres.doctor_name,
						'prescription_date': pres.prescription_date.isoformat(),
						'diagnosis': pres.diagnosis,
						'notes': pres.notes,
						'tenant': pres.tenant.id
					} for pres in Prescription.objects.filter(tenant=tenant)
				]
				export_data['module_data']['pharmacy'] = pharmacy_data
				
				# Export Retail Module Data (filtered by tenant)
				retail_data = {}
				retail_data['products'] = ProductSerializer(Product.objects.filter(tenant=tenant), many=True).data
				retail_data['customers'] = RetailCustomerSerializer(RetailCustomer.objects.filter(tenant=tenant), many=True).data
				retail_data['sales'] = RetailSaleSerializer(RetailSale.objects.filter(tenant=tenant), many=True).data
				retail_data['suppliers'] = [
					{
						'id': sup.id,
						'name': sup.name,
						'contact_person': sup.contact_person,
						'phone': sup.phone,
						'email': sup.email,
						'address': sup.address,
						'tenant': sup.tenant.id
					} for sup in Supplier.objects.filter(tenant=tenant)
				]
				retail_data['warehouses'] = [
					{
						'id': wh.id,
						'name': wh.name,
						'address': wh.address,
						'contact_person': wh.contact_person,
						'phone': wh.phone,
						'tenant': wh.tenant.id
					} for wh in Warehouse.objects.filter(tenant=tenant)
				]
				export_data['module_data']['retail'] = retail_data
				
				# Create JSON file
				json_file_path = os.path.join(temp_dir, 'zenith_erp_export.json')
				with open(json_file_path, 'w') as f:
					json.dump(export_data, f, indent=2, cls=DecimalEncoder)
				
				# Create ZIP file
				zip_file_path = os.path.join(temp_dir, 'zenith_erp_export.zip')
				with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
					zipf.write(json_file_path, 'zenith_erp_export.json')
					
					# Add README file
					readme_content = f"""
Zenith ERP Data Export
======================

Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Exported By: {request.user.username}
Tenant: {tenant.name}

This export contains:
- System configuration (users, tenant, roles, plans)
- Education module data (students, classes, fees, attendance)
- Pharmacy module data (medicines, customers, sales, prescriptions)
- Retail module data (products, customers, sales, suppliers, warehouses)
- New module flags in plans and tenant: hotel, restaurant, salon

To import this data, use the Import Data feature in the Admin Dashboard.
					"""
					zipf.writestr('README.txt', readme_content)
				
				# Return ZIP file as response
				with open(zip_file_path, 'rb') as f:
					response = HttpResponse(f.read(), content_type='application/zip')
					response['Content-Disposition'] = f'attachment; filename="zenith-erp-export-{datetime.now().strftime("%Y%m%d-%H%M%S")}.zip"'
					return response
					
		except Exception as e:
			import traceback
			print(f"Admin export error: {str(e)}")
			print(traceback.format_exc())
			return Response({'error': f'Export failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AdminImportDataView(APIView):
	authentication_classes = [JWTAuthentication]
	permission_classes = [IsAuthenticated]
	
	def post(self, request):
		"""Import system data from a ZIP file"""
		try:
			# Check if user is admin
			try:
				user_profile = UserProfile.objects.get(user=request.user)
			except UserProfile.DoesNotExist:
				return Response({'error': 'User profile not found'}, status=status.HTTP_404_NOT_FOUND)
			
			if not user_profile.role or user_profile.role.name != 'admin':
				return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
			
			# Check if file was uploaded
			if 'file' not in request.FILES:
				return Response({'error': 'No file uploaded'}, status=status.HTTP_400_BAD_REQUEST)
			
			uploaded_file = request.FILES['file']
			
			# Validate file type
			if not uploaded_file.name.endswith('.zip'):
				return Response({'error': 'Only ZIP files are supported'}, status=status.HTTP_400_BAD_REQUEST)
			
			# Create temporary directory for import
			with tempfile.TemporaryDirectory() as temp_dir:
				# Save uploaded file
				file_path = os.path.join(temp_dir, uploaded_file.name)
				with open(file_path, 'wb') as f:
					for chunk in uploaded_file.chunks():
						f.write(chunk)
				
				# Extract ZIP file
				with zipfile.ZipFile(file_path, 'r') as zipf:
					# Look for JSON file
					json_files = [f for f in zipf.namelist() if f.endswith('.json')]
					if not json_files:
						return Response({'error': 'No JSON data file found in ZIP'}, status=status.HTTP_400_BAD_REQUEST)
					
					# Extract and read JSON data
					json_file_name = json_files[0]
					with zipf.open(json_file_name) as json_file:
						import_data = json.load(json_file)
			
			# Validate import data structure
			if 'export_info' not in import_data or 'system_data' not in import_data or 'module_data' not in import_data:
				return Response({'error': 'Invalid export file format'}, status=status.HTTP_400_BAD_REQUEST)
			
			# Import system data (basic validation only - full import would need more complex logic)
			imported_count = 0
			
			# Count items that would be imported
			if 'users' in import_data['system_data']:
				imported_count += len(import_data['system_data']['users'])
			
			if 'module_data' in import_data:
				if 'education' in import_data['module_data']:
					if 'students' in import_data['module_data']['education']:
						imported_count += len(import_data['module_data']['education']['students'])
					if 'classes' in import_data['module_data']['education']:
						imported_count += len(import_data['module_data']['education']['classes'])
				
				if 'pharmacy' in import_data['module_data']:
					if 'medicines' in import_data['module_data']['pharmacy']:
						imported_count += len(import_data['module_data']['pharmacy']['medicines'])
					if 'customers' in import_data['module_data']['pharmacy']:
						imported_count += len(import_data['module_data']['pharmacy']['customers'])
				
				if 'retail' in import_data['module_data']:
					if 'products' in import_data['module_data']['retail']:
						imported_count += len(import_data['module_data']['retail']['products'])
					if 'customers' in import_data['module_data']['retail']:
						imported_count += len(import_data['module_data']['retail']['customers'])
			
			return Response({
				'message': f'Import file validated successfully. Found {imported_count} items to import.',
				'import_info': import_data.get('export_info', {}),
				'item_count': imported_count
			}, status=status.HTTP_200_OK)
			
		except Exception as e:
			return Response({'error': f'Import failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 

class TenantPublicSettingsView(APIView):
	authentication_classes = [JWTAuthentication]
	permission_classes = [IsAuthenticated]

	def get(self, request):
		try:
			try:
				profile = UserProfile.objects.get(user=request.user)
			except UserProfile.DoesNotExist:
				return Response({'error': 'User profile not found'}, status=status.HTTP_404_NOT_FOUND)
			if not profile.role or profile.role.name != 'admin':
				return Response({'error': 'Admin access required'}, status=403)
			
			# Check if user has a paid plan
			tenant = profile.tenant
			if not tenant or not tenant.plan:
				return Response({
					'error': 'Public settings are only available for paid plans. Please upgrade to access this feature.',
					'requires_paid_plan': True
				}, status=403)
			
			plan = tenant.plan
			# Free plan users cannot access (price = 0)
			if plan.price is not None and plan.price == 0:
				return Response({
					'error': 'Public settings are only available for paid plans. Please upgrade from the Free plan to access this feature.',
					'requires_paid_plan': True,
					'current_plan': plan.name
				}, status=403)
			
			serializer = TenantSerializer(tenant, context={'request': request})
			settings_data = {
				'slug': tenant.slug,
				'public_booking_enabled': tenant.public_booking_enabled,
				'public_orders_enabled': tenant.public_orders_enabled,
				'public_admissions_enabled': tenant.public_admissions_enabled,
				'has_api_key': bool(tenant.public_api_key),
				'public_api_key': tenant.public_api_key or '',
				'logo': serializer.data.get('logo_url'),
				'logo_url': serializer.data.get('logo_url'),
				# Education module percentage calculation settings
				'percentage_calculation_method': getattr(tenant, 'percentage_calculation_method', 'SIMPLE'),
				'percentage_calculation_scope': getattr(tenant, 'percentage_calculation_scope', 'TERM_WISE'),
				'percentage_excluded_subjects': getattr(tenant, 'percentage_excluded_subjects', []),
				'percentage_rounding': getattr(tenant, 'percentage_rounding', 2),
			}
			return Response(settings_data)
		except Exception as e:
			return Response({'error': str(e)}, status=400)

	def post(self, request):
		try:
			try:
				profile = UserProfile.objects.get(user=request.user)
			except UserProfile.DoesNotExist:
				return Response({'error': 'User profile not found'}, status=status.HTTP_404_NOT_FOUND)
			if not profile.role or profile.role.name != 'admin':
				return Response({'error': 'Admin access required'}, status=403)
			
			# Check if user has a paid plan
			tenant = profile.tenant
			if not tenant or not tenant.plan:
				return Response({
					'error': 'Public settings are only available for paid plans. Please upgrade to access this feature.',
					'requires_paid_plan': True
				}, status=403)
			
			plan = tenant.plan
			# Free plan users cannot access (price = 0)
			if plan.price is not None and plan.price == 0:
				return Response({
					'error': 'Public settings are only available for paid plans. Please upgrade from the Free plan to access this feature.',
					'requires_paid_plan': True,
					'current_plan': plan.name
				}, status=403)
			data = request.data or {}
			
			# Handle logo upload
			if 'logo' in request.FILES:
				tenant.logo = request.FILES['logo']
				tenant.save(update_fields=['logo'])
			
			# Handle logo deletion
			if data.get('delete_logo') == True:
				if tenant.logo:
					tenant.logo.delete(save=False)
				tenant.logo = None
				tenant.save(update_fields=['logo'])
			
			new_slug = data.get('slug')
			if new_slug is not None:
				new_slug = slugify(new_slug)
				if not new_slug:
					return Response({'error': 'Invalid slug'}, status=400)
				from api.models.user import Tenant as TenantModel
				if TenantModel.objects.exclude(id=tenant.id).filter(slug=new_slug).exists():
					return Response({'error': 'Slug already in use'}, status=409)
				tenant.slug = new_slug
			if 'public_booking_enabled' in data:
				tenant.public_booking_enabled = bool(data.get('public_booking_enabled'))
			if 'public_orders_enabled' in data:
				tenant.public_orders_enabled = bool(data.get('public_orders_enabled'))
			if 'public_admissions_enabled' in data:
				tenant.public_admissions_enabled = bool(data.get('public_admissions_enabled'))
			if data.get('generate_api_key'):
				tenant.public_api_key = secrets.token_urlsafe(32)
			# Education module percentage calculation settings
			if 'percentage_calculation_method' in data:
				method = data.get('percentage_calculation_method', 'SIMPLE')
				if method in ['SIMPLE', 'SUBJECT_WISE', 'WEIGHTED']:
					tenant.percentage_calculation_method = method
				else:
					return Response({'error': 'Invalid calculation method. Must be SIMPLE, SUBJECT_WISE, or WEIGHTED'}, status=400)
			
			if 'percentage_excluded_subjects' in data:
				excluded = data.get('percentage_excluded_subjects')
				if isinstance(excluded, list):
					# Validate that all subject IDs exist and belong to tenant
					from education.models import Subject
					valid_subject_ids = []
					for sub_id in excluded:
						if isinstance(sub_id, int) or (isinstance(sub_id, str) and sub_id.isdigit()):
							sub_id_int = int(sub_id)
							if Subject.objects.filter(id=sub_id_int, tenant=tenant).exists():
								valid_subject_ids.append(sub_id_int)
					tenant.percentage_excluded_subjects = valid_subject_ids
				elif isinstance(excluded, str):
					# Try to parse JSON string
					import json
					try:
						parsed = json.loads(excluded)
						if isinstance(parsed, list):
							# Validate subject IDs
							from education.models import Subject
							valid_subject_ids = []
							for sub_id in parsed:
								if isinstance(sub_id, int) or (isinstance(sub_id, str) and sub_id.isdigit()):
									sub_id_int = int(sub_id)
									if Subject.objects.filter(id=sub_id_int, tenant=tenant).exists():
										valid_subject_ids.append(sub_id_int)
							tenant.percentage_excluded_subjects = valid_subject_ids
						else:
							tenant.percentage_excluded_subjects = []
					except:
						tenant.percentage_excluded_subjects = []
				else:
					tenant.percentage_excluded_subjects = []
			
			if 'percentage_calculation_scope' in data:
				scope = data.get('percentage_calculation_scope', 'TERM_WISE')
				if scope in ['TERM_WISE', 'ALL_TERMS']:
					tenant.percentage_calculation_scope = scope
				else:
					return Response({'error': 'Invalid calculation scope. Must be TERM_WISE or ALL_TERMS'}, status=400)
			
			if 'percentage_rounding' in data:
				rounding = data.get('percentage_rounding')
				if rounding in [0, 1, 2]:
					tenant.percentage_rounding = rounding
				else:
					return Response({'error': 'Invalid rounding value. Must be 0, 1, or 2'}, status=400)
			tenant.save()
			serializer = TenantSerializer(tenant, context={'request': request})
			return Response({
				'message': 'Settings updated', 
				'slug': tenant.slug,
				'percentage_calculation_method': tenant.percentage_calculation_method,
				'percentage_calculation_scope': tenant.percentage_calculation_scope,
				'percentage_excluded_subjects': tenant.percentage_excluded_subjects,
				'percentage_rounding': tenant.percentage_rounding, 
				'has_api_key': bool(tenant.public_api_key), 
				'public_api_key': tenant.public_api_key or '',
				'logo_url': serializer.data.get('logo_url')
			})
		except Exception as e:
			return Response({'error': str(e)}, status=400)

class TenantLogoView(APIView):
	"""Dedicated endpoint for tenant logo upload/delete"""
	authentication_classes = [JWTAuthentication]
	permission_classes = [IsAuthenticated]

	def get(self, request):
		"""Get current logo URL"""
		try:
			try:
				profile = UserProfile.objects.get(user=request.user)
			except UserProfile.DoesNotExist:
				return Response({'error': 'User profile not found'}, status=status.HTTP_404_NOT_FOUND)
			if not profile.role or profile.role.name != 'admin':
				return Response({'error': 'Admin access required'}, status=403)
			tenant = profile.tenant
			serializer = TenantSerializer(tenant, context={'request': request})
			return Response({
				'logo_url': serializer.data.get('logo_url'),
				'has_logo': bool(tenant.logo)
			})
		except Exception as e:
			return Response({'error': str(e)}, status=400)

	def post(self, request):
		"""Upload logo"""
		try:
			try:
				profile = UserProfile.objects.get(user=request.user)
			except UserProfile.DoesNotExist:
				return Response({'error': 'User profile not found'}, status=status.HTTP_404_NOT_FOUND)
			if not profile.role or profile.role.name != 'admin':
				return Response({'error': 'Admin access required'}, status=403)
			
			if 'logo' not in request.FILES:
				return Response({'error': 'No logo file provided'}, status=400)
			
			tenant = profile.tenant
			
			# Delete old logo if exists
			if tenant.logo:
				tenant.logo.delete(save=False)
			
			# Save new logo
			tenant.logo = request.FILES['logo']
			tenant.save(update_fields=['logo'])
			
			serializer = TenantSerializer(tenant, context={'request': request})
			return Response({
				'message': 'Logo uploaded successfully',
				'logo_url': serializer.data.get('logo_url')
			})
		except Exception as e:
			return Response({'error': str(e)}, status=400)

	def delete(self, request):
		"""Delete logo"""
		try:
			try:
				profile = UserProfile.objects.get(user=request.user)
			except UserProfile.DoesNotExist:
				return Response({'error': 'User profile not found'}, status=status.HTTP_404_NOT_FOUND)
			if not profile.role or profile.role.name != 'admin':
				return Response({'error': 'Admin access required'}, status=403)
			
			tenant = profile.tenant
			if tenant.logo:
				tenant.logo.delete(save=False)
				tenant.logo = None
				tenant.save(update_fields=['logo'])
				return Response({'message': 'Logo deleted successfully'})
			return Response({'message': 'No logo to delete'})
		except Exception as e:
			return Response({'error': str(e)}, status=400)