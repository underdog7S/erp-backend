import os
import requests
from time import time
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.cache import cache
from api.models.user import Tenant
from salon.models import Service as SalonService, Stylist as SalonStylist, Appointment as SalonAppointment
from django.db import transaction
from datetime import datetime, timedelta
from retail.models import Product as RetailProduct
from education.models import Class as EduClass, AdmissionApplication as EduApplication, Student
import logging

logger = logging.getLogger(__name__)


class APIRootView(APIView):
    """Simple root endpoint for /api - Limited info for security"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        # Don't expose too much information to public
        return Response({
            "name": "Zenith ERP API",
            "version": "1.0.0",
            "status": "active",
            "message": "Use /api/login/ to authenticate and access endpoints",
            "endpoints": {
                "authentication": "/api/login/",
                "registration": "/api/register/",
                "documentation": "Visit /swagger/ or /redoc/ for API documentation (authentication required)"
            },
            "note": "Most endpoints require authentication. Please log in to access full API."
        })


def get_tenant_or_404(slug: str) -> Tenant:
	return get_object_or_404(Tenant, slug=slug)


def validate_api_key(request, tenant: Tenant):
	key = request.headers.get('X-API-Key') or request.query_params.get('api_key')
	if not key or not tenant.public_api_key or key != tenant.public_api_key:
		return False
	return True

def verify_recaptcha(request):
	secret = os.getenv('RECAPTCHA_SECRET')
	if not secret:
		return True
	token = request.headers.get('X-Recaptcha-Token') or (request.data.get('recaptcha_token') if hasattr(request, 'data') else None)
	if not token:
		return False
	try:
		resp = requests.post('https://www.google.com/recaptcha/api/siteverify', data={
			'secret': secret,
			'response': token,
			'remoteip': request.META.get('REMOTE_ADDR')
		}, timeout=10)
		j = resp.json()
		return bool(j.get('success'))
	except Exception:
		return False

def check_rate_limit(request, key_prefix: str, limit: int = 10, window_seconds: int = 60):
	ip = request.META.get('REMOTE_ADDR', 'unknown')
	cache_key = f"rl:{key_prefix}:{ip}"
	data = cache.get(cache_key)
	now = int(time())
	if not data:
		cache.set(cache_key, { 'start': now, 'count': 1 }, window_seconds)
		return True
	start = data.get('start', now)
	count = data.get('count', 0)
	if now - start >= window_seconds:
		cache.set(cache_key, { 'start': now, 'count': 1 }, window_seconds)
		return True
	if count + 1 > limit:
		return False
	data['count'] = count + 1
	cache.set(cache_key, data, window_seconds - (now - start))
	return True



class PublicSalonServicesView(APIView):
	permission_classes = [AllowAny]
	authentication_classes = []
	def get(self, request, slug):
		tenant = get_tenant_or_404(slug)
		if not tenant.public_booking_enabled:
			return Response({'error': 'Public booking disabled'}, status=403)
		services = SalonService.objects.filter(tenant=tenant, is_active=True)
		data = [{'id': s.id, 'name': s.name, 'price': float(s.price), 'duration_minutes': s.duration_minutes} for s in services]
		return Response({'services': data})


class PublicSalonStylistsView(APIView):
	permission_classes = [AllowAny]
	authentication_classes = []
	def get(self, request, slug):
		tenant = get_tenant_or_404(slug)
		if not tenant.public_booking_enabled:
			return Response({'error': 'Public booking disabled'}, status=403)
		stylists = SalonStylist.objects.filter(tenant=tenant, is_active=True)
		data = [{'id': st.id, 'first_name': st.first_name, 'last_name': st.last_name} for st in stylists]
		return Response({'stylists': data})


class PublicSalonAppointmentCreateView(APIView):
	permission_classes = [AllowAny]
	authentication_classes = []
	def post(self, request, slug):
		tenant = get_tenant_or_404(slug)
		if not tenant.public_booking_enabled:
			return Response({'error': 'Public booking disabled'}, status=403)
		if not validate_api_key(request, tenant):
			return Response({'error': 'Invalid API key'}, status=401)
		if not verify_recaptcha(request):
			return Response({'error': 'reCAPTCHA failed'}, status=400)
		if not check_rate_limit(request, f"salon_appt:{tenant.slug}", limit=5, window_seconds=60):
			return Response({'error': 'Too many requests'}, status=429)
		payload = request.data
		try:
			# Input validation
			service_id = payload.get('service')
			stylist_id = payload.get('stylist')
			customer_name = payload.get('customer_name', '').strip()
			customer_phone = (payload.get('customer_phone') or '').strip()
			start_time_raw = payload.get('start_time')
			end_time_raw = payload.get('end_time')
			price_raw = payload.get('price', 0)
			
			# Validate required fields
			if not start_time_raw:
				return Response({'error': 'start_time is required'}, status=400)
			if not customer_name:
				return Response({'error': 'customer_name is required'}, status=400)
			if not customer_phone:
				return Response({'error': 'customer_phone is required'}, status=400)
			if not service_id:
				return Response({'error': 'service is required'}, status=400)
			if not stylist_id:
				return Response({'error': 'stylist is required'}, status=400)
			
			# Validate and convert IDs
			try:
				service_id = int(service_id)
				stylist_id = int(stylist_id)
			except (ValueError, TypeError):
				return Response({'error': 'Invalid service or stylist ID format'}, status=400)
			
			# Validate and parse datetime
			try:
				start_dt = datetime.fromisoformat(start_time_raw.replace('Z', '+00:00'))
			except (ValueError, AttributeError) as e:
				return Response({'error': f'Invalid start_time format: {str(e)}'}, status=400)
			
			# Validate price
			try:
				price = float(price_raw) if price_raw else 0
				if price < 0:
					return Response({'error': 'Price cannot be negative'}, status=400)
			except (ValueError, TypeError):
				return Response({'error': 'Invalid price format'}, status=400)
			
			# Validate phone number format (basic check)
			if len(customer_phone) < 10:
				return Response({'error': 'Invalid phone number format'}, status=400)
			
			# Get service and stylist with tenant validation
			try:
				service = SalonService.objects.get(id=service_id, tenant=tenant, is_active=True)
			except SalonService.DoesNotExist:
				return Response({'error': 'Service not found or not available'}, status=404)
			
			try:
				stylist = SalonStylist.objects.get(id=stylist_id, tenant=tenant, is_active=True)
			except SalonStylist.DoesNotExist:
				return Response({'error': 'Stylist not found or not available'}, status=404)
			
			# Determine end time by service duration if not provided
			if end_time_raw:
				try:
					end_dt = datetime.fromisoformat(end_time_raw.replace('Z', '+00:00'))
				except (ValueError, AttributeError) as e:
					return Response({'error': f'Invalid end_time format: {str(e)}'}, status=400)
			else:
				duration_min = getattr(service, 'duration_minutes', None) or 30
				end_dt = start_dt + timedelta(minutes=duration_min)
			
			# Validate time range
			if end_dt <= start_dt:
				return Response({'error': 'End time must be after start time'}, status=400)
			
			# Overlap check within a transaction
			with transaction.atomic():
				conflict = SalonAppointment.objects.select_for_update().filter(
					tenant=tenant,
					stylist=stylist,
					start_time__lt=end_dt,
					end_time__gt=start_dt,
					status__in=['scheduled', 'in_progress']
				).exists()
				if conflict:
					return Response({'error': 'Time slot not available'}, status=409)
				
				appt = SalonAppointment.objects.create(
					tenant=tenant,
					service=service,
					stylist=stylist,
					customer_name=customer_name,
					customer_phone=customer_phone,
					start_time=start_dt,
					end_time=end_dt,
					price=price,
					status='scheduled',
				)
			return Response({'id': appt.id, 'status': appt.status}, status=201)
		except Exception as e:
			import logging
			logger = logging.getLogger(__name__)
			logger.error(f"Error creating public salon appointment: {str(e)}", exc_info=True)
			return Response({'error': 'An error occurred while creating appointment. Please try again.'}, status=500)


class PublicRetailProductsView(APIView):
	permission_classes = [AllowAny]
	authentication_classes = []
	def get(self, request, slug):
		tenant = get_tenant_or_404(slug)
		if not tenant.public_orders_enabled:
			return Response({'error': 'Public orders disabled'}, status=403)
		products = RetailProduct.objects.filter(tenant=tenant, is_active=True)
		data = [{'id': p.id, 'name': p.name, 'sku': p.sku, 'price': float(p.selling_price)} for p in products[:100]]
		return Response({'products': data})


class PublicRetailOrderCreateView(APIView):
	permission_classes = [AllowAny]
	authentication_classes = []
	def post(self, request, slug):
		tenant = get_tenant_or_404(slug)
		if not tenant.public_orders_enabled:
			return Response({'error': 'Public orders disabled'}, status=403)
		if not validate_api_key(request, tenant):
			return Response({'error': 'Invalid API key'}, status=401)
		if not verify_recaptcha(request):
			return Response({'error': 'reCAPTCHA failed'}, status=400)
		if not check_rate_limit(request, f"retail_order:{tenant.slug}", limit=10, window_seconds=60):
			return Response({'error': 'Too many requests'}, status=429)
		# This is a placeholder to accept an order cart and queue it for ERP processing
		cart = request.data.get('items', [])
		customer = request.data.get('customer', {})
		if not cart:
			return Response({'error': 'Empty cart'}, status=400)
		return Response({'message': 'Order received', 'items_count': len(cart)}, status=201)


class PublicEducationClassesView(APIView):
	permission_classes = [AllowAny]
	authentication_classes = []
	def get(self, request, slug):
		tenant = get_tenant_or_404(slug)
		if not tenant.public_admissions_enabled:
			return Response({'error': 'Public admissions disabled'}, status=403)
		classes = EduClass.objects.filter(tenant=tenant)
		data = [{'id': c.id, 'name': c.name} for c in classes]
		return Response({'classes': data})


class PublicEducationAdmissionCreateView(APIView):
	permission_classes = [AllowAny]
	authentication_classes = []
	def post(self, request, slug):
		tenant = get_tenant_or_404(slug)
		if not tenant.public_admissions_enabled:
			return Response({'error': 'Public admissions disabled'}, status=403)
		if not validate_api_key(request, tenant):
			return Response({'error': 'Invalid API key'}, status=401)
		if not verify_recaptcha(request):
			return Response({'error': 'reCAPTCHA failed'}, status=400)
		if not check_rate_limit(request, f"edu_adm:{tenant.slug}", limit=5, window_seconds=60):
			return Response({'error': 'Too many requests'}, status=429)
		payload = request.data
		try:
			# Input validation
			applicant_name = payload.get('name', '').strip()
			email = payload.get('email', '').strip()
			phone = payload.get('phone', '').strip()
			upper_id = payload.get('upper_id', '').strip()
			class_id = payload.get('class_id')
			notes = payload.get('notes', '').strip()
			
			# Validate required fields
			if not applicant_name:
				return Response({'error': 'name is required'}, status=400)
			if not email:
				return Response({'error': 'email is required'}, status=400)
			if not phone:
				return Response({'error': 'phone is required'}, status=400)
			if not class_id:
				return Response({'error': 'class_id is required'}, status=400)
			
			# Validate email format
			if '@' not in email or '.' not in email.split('@')[-1]:
				return Response({'error': 'Invalid email format'}, status=400)
			
			# Validate phone number format (basic check)
			if len(phone) < 10:
				return Response({'error': 'Invalid phone number format'}, status=400)
			
			# Validate class_id
			try:
				class_id = int(class_id)
			except (ValueError, TypeError):
				return Response({'error': 'Invalid class_id format'}, status=400)
			
			# Check if class exists and belongs to tenant
			try:
				desired_class = EduClass.objects.get(id=class_id, tenant=tenant)
			except EduClass.DoesNotExist:
				return Response({'error': 'Class not found'}, status=404)
			
			# Check if student with upper_id already exists
			if upper_id and Student.objects.filter(tenant=tenant, upper_id__iexact=upper_id).exists():
				return Response({'error': 'Student with this roll number already exists'}, status=409)
			
			# Create admission application
			app = EduApplication.objects.create(
				tenant=tenant,
				applicant_name=applicant_name,
				email=email,
				phone=phone,
				desired_class=desired_class,
				notes=notes,
				status='pending'
			)
			return Response({'id': app.id, 'status': app.status}, status=201)
		except Exception as e:
			import logging
			logger = logging.getLogger(__name__)
			logger.error(f"Error creating public education admission: {str(e)}", exc_info=True)
			return Response({'error': 'An error occurred while creating admission application. Please try again.'}, status=500)

class SitemapView(APIView):
	"""Generate sitemap.xml for SEO"""
	permission_classes = [AllowAny]
	authentication_classes = []
	
	def get(self, request):
		from django.http import HttpResponse
		from datetime import datetime
		
		base_url = 'https://zenitherp.online'
		current_date = datetime.now().strftime('%Y-%m-%d')
		
		# Public pages that should be indexed
		public_pages = [
			{'url': '', 'priority': '1.0', 'changefreq': 'weekly'},
			{'url': '/about', 'priority': '0.8', 'changefreq': 'monthly'},
			{'url': '/pricing', 'priority': '0.9', 'changefreq': 'monthly'},
			{'url': '/faq', 'priority': '0.7', 'changefreq': 'monthly'},
			{'url': '/contact', 'priority': '0.8', 'changefreq': 'monthly'},
			{'url': '/privacy', 'priority': '0.5', 'changefreq': 'yearly'},
			{'url': '/terms', 'priority': '0.5', 'changefreq': 'yearly'},
			{'url': '/refund', 'priority': '0.5', 'changefreq': 'yearly'},
			{'url': '/delivery', 'priority': '0.5', 'changefreq': 'yearly'},
		]
		
		sitemap = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:schemaLocation="http://www.sitemaps.org/schemas/sitemap/0.9
        http://www.sitemaps.org/schemas/sitemap/0.9/sitemap.xsd">
'''
		
		for page in public_pages:
			sitemap += f'''  <url>
    <loc>{base_url}{page['url']}</loc>
    <lastmod>{current_date}</lastmod>
    <changefreq>{page['changefreq']}</changefreq>
    <priority>{page['priority']}</priority>
  </url>
'''
		
		sitemap += '</urlset>'
		
		response = HttpResponse(sitemap, content_type='application/xml')
		return response

