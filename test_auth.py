#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings')
django.setup()

from django.contrib.auth.models import User
from api.models.user import Tenant, UserProfile
from pharmacy.models import Medicine

def test_auth():
    """Test authentication and user setup"""
    
    print("Testing authentication setup...")
    print("-" * 40)
    
    # Check if admin user exists
    try:
        admin_user = User.objects.get(username='admin')
        print(f"✅ Admin user exists: {admin_user.username}")
        print(f"   Email: {admin_user.email}")
        print(f"   Is active: {admin_user.is_active}")
        print(f"   Is staff: {admin_user.is_staff}")
        print(f"   Is superuser: {admin_user.is_superuser}")
    except User.DoesNotExist:
        print("❌ Admin user does not exist")
        return
    
    # Check if tenant exists
    try:
        tenant = Tenant.objects.get(name="Test Pharmacy")
        print(f"✅ Tenant exists: {tenant.name}")
    except Tenant.DoesNotExist:
        print("❌ Tenant does not exist")
        return
    
    # Check if user profile exists
    try:
        user_profile = UserProfile.objects.get(user=admin_user, tenant=tenant)
        print(f"✅ User profile exists for admin in Test Pharmacy")
        print(f"   Role: {user_profile.role}")
        print(f"   Department: {user_profile.department}")
    except UserProfile.DoesNotExist:
        print("❌ User profile does not exist for admin in Test Pharmacy")
        return
    
    # Check medicines for this tenant
    medicines = Medicine.objects.filter(tenant=tenant)
    print(f"✅ Medicines in tenant: {medicines.count()}")
    
    # Check specific barcode
    barcode = '8901234567890'
    medicine = medicines.filter(barcode=barcode).first()
    if medicine:
        print(f"✅ Found medicine with barcode {barcode}: {medicine.name}")
    else:
        print(f"❌ No medicine found with barcode {barcode}")

if __name__ == '__main__':
    test_auth() 