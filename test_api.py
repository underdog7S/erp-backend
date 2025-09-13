#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings')
django.setup()

from pharmacy.models import Medicine
from api.models.user import Tenant, UserProfile, Role
from django.contrib.auth.models import User

def test_medicine_search():
    """Test the medicine search functionality"""
    
    # Get the tenant and user
    tenant = Tenant.objects.get(name="Test Pharmacy")
    user = User.objects.get(username='admin')
    user_profile = UserProfile.objects.get(user=user, tenant=tenant)
    
    print(f"Testing with tenant: {tenant.name}")
    print(f"Testing with user: {user.username}")
    
    # Test barcode search
    test_barcodes = [
        '1234567890123',
        '2345678901234', 
        '3456789012345',
        '4567890123456',
        '5678901234567',
        '8901234567890'
    ]
    
    print("\nTesting barcode search:")
    print("-" * 40)
    
    for barcode in test_barcodes:
        # Direct database query
        medicine = Medicine.objects.filter(tenant=tenant, barcode=barcode).first()
        
        if medicine:
            print(f"✅ Database: {barcode} -> {medicine.name}")
        else:
            print(f"❌ Database: {barcode} -> Not found")
    
    # Test the search logic from the view
    print("\nTesting search logic:")
    print("-" * 40)
    
    for barcode in test_barcodes:
        queryset = Medicine.objects.filter(tenant=tenant)
        medicine = queryset.filter(barcode=barcode).first()
        
        if medicine:
            print(f"✅ Search: {barcode} -> {medicine.name}")
        else:
            print(f"❌ Search: {barcode} -> Not found")

if __name__ == '__main__':
    test_medicine_search() 