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


class APIRootView(APIView):
    """Simple root endpoint for /api"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        return Response({
            "name": "Zenith ERP API",
            "version": "1.0.0",
            "status": "active",
            "endpoints": {
                "authentication": "/api/login/",
                "registration": "/api/register/",
                "users": "/api/users/",
                "documentation": "Visit /swagger/ for API documentation"
            }
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
			service_id = int(payload.get('service'))
			stylist_id = int(payload.get('stylist'))
			customer_name = payload.get('customer_name')
			customer_phone = (payload.get('customer_phone') or '').strip()
			start_time_raw = payload.get('start_time')
			end_time_raw = payload.get('end_time')
			if not start_time_raw:
				return Response({'error': 'start_time required'}, status=400)
			# Parse datetimes (expecting ISO 8601)
			start_dt = datetime.fromisoformat(start_time_raw)
			price = float(payload.get('price') or 0)
			if not (service_id and stylist_id and customer_name and start_dt and customer_phone):
				return Response({'error': 'Missing fields'}, status=400)
			service = SalonService.objects.get(id=service_id, tenant=tenant)
			stylist = SalonStylist.objects.get(id=stylist_id, tenant=tenant)
			# Determine end time by service duration if not provided
			if end_time_raw:
				end_dt = datetime.fromisoformat(end_time_raw)
			else:
				duration_min = getattr(service, 'duration_minutes', None) or 30
				end_dt = start_dt + timedelta(minutes=duration_min)
			# Overlap check within a transaction
			with transaction.atomic():
				conflict = SalonAppointment.objects.select_for_update().filter(
					tenant=tenant,
					stylist=stylist,
					start_time__lt=end_dt,
					end_time__gt=start_dt
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
			return Response({'error': str(e)}, status=400)


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
		if Student.objects.filter(tenant=tenant, upper_id__iexact=payload.get('upper_id')).exists():
			return Response({'error': 'Student upper_id already exists'}, status=409)
		app = EduApplication.objects.create(
			tenant=tenant,
			applicant_name=payload.get('name'),
			email=payload.get('email'),
			phone=payload.get('phone', ''),
			desired_class_id=payload.get('class_id'),
			notes=payload.get('notes', ''),
		)
		return Response({'id': app.id, 'status': app.status}, status=201)

