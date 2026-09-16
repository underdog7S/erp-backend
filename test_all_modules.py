import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings')
django.setup()

from django.test import RequestFactory
from rest_framework.test import APIRequestFactory, force_authenticate
from django.contrib.auth import get_user_model
from django.urls import resolve

User = get_user_model()
try:
    user = User.objects.get(username='shadab1')
except User.DoesNotExist:
    user = User.objects.first()

from django.apps import apps
Tenant = apps.get_model('api', 'Tenant')
Plan = apps.get_model('api', 'Plan')

enterprise_plan, _ = Plan._default_manager.get_or_create(
    name='Enterprise',
    defaults={
        'price': 99.00,
        'has_crm': True,
        'has_education': True,
        'has_pharmacy': True,
        'has_retail': True,
        'has_salon': True,
        'has_hotel': True,
        'has_restaurant': True,
        'has_analytics': True,
        'has_inventory': True,
        'has_pos': True,
    }
)

# Ensure enterprise has all features
enterprise_plan.has_crm = True
enterprise_plan.has_education = True
enterprise_plan.has_pharmacy = True
enterprise_plan.has_retail = True
enterprise_plan.has_salon = True
enterprise_plan.has_hotel = True
enterprise_plan.has_restaurant = True
enterprise_plan.save()

tenant = user.userprofile.tenant
tenant.plan = enterprise_plan
tenant.save()

rf = APIRequestFactory()

endpoints_to_test = [
    # CRM
    '/api/crm/customers/',
    '/api/crm/leads/',
    '/api/crm/campaigns/',
    # Pharmacy
    '/api/pharmacy/medicines/',
    '/api/pharmacy/suppliers/',
    '/api/pharmacy/sales/',
    # Retail
    '/api/retail/products/',
    '/api/retail/suppliers/',
    '/api/retail/sales/',
    # Salon
    '/api/salon/services/',
    '/api/salon/appointments/',
    '/api/salon/staff/',
    # Hotel
    '/api/hotel/rooms/',
    '/api/hotel/bookings/',
    # Restaurant
    '/api/restaurant/menu-items/',
    '/api/restaurant/orders/',
]

print("Testing core module endpoints...")
success_count = 0
failed_endpoints = []

for url in endpoints_to_test:
    request = rf.get(url)
    force_authenticate(request, user=user)
    try:
        match = resolve(url)
        view_func = match.func
        response = view_func(request, *match.args, **match.kwargs)
        if response.status_code in [200, 201]:
            print(f"[OK] {url} -> {response.status_code}")
            success_count += 1
        else:
            print(f"[FAIL] {url} -> {response.status_code}")
            if hasattr(response, 'data'):
                print(response.data)
            failed_endpoints.append(url)
    except Exception as e:
        print(f"[ERROR] {url} -> {str(e)}")
        failed_endpoints.append(url)

print(f"\nSummary: {success_count}/{len(endpoints_to_test)} endpoints passed.")
if failed_endpoints:
    print("Failed endpoints:", failed_endpoints)
