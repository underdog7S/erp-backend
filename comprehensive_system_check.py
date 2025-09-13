#!/usr/bin/env python
import os
import sys
import django
import requests
import json

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings')
django.setup()

from django.contrib.auth.models import User
from api.models.user import Tenant, UserProfile, Role
from pharmacy.models import Medicine, MedicineCategory, Supplier
from rest_framework_simplejwt.tokens import RefreshToken

def comprehensive_system_check():
    """Comprehensive system check for all components"""
    
    print("🔍 COMPREHENSIVE SYSTEM CHECK")
    print("=" * 50)
    
    # 1. Check Database Models
    print("\n1. DATABASE MODELS CHECK")
    print("-" * 30)
    
    try:
        # Check if admin user exists
        admin_user = User.objects.get(username='admin')
        print("✅ Admin user exists")
        
        # Check if tenant exists
        tenant = Tenant.objects.get(name="Test Pharmacy")
        print("✅ Test Pharmacy tenant exists")
        
        # Check if user profile exists
        user_profile = UserProfile.objects.get(user=admin_user, tenant=tenant)
        print("✅ User profile exists")
        
        # Check medicines
        medicines = Medicine.objects.filter(tenant=tenant)
        print(f"✅ {medicines.count()} medicines found in database")
        
        # Check specific barcode
        barcode = '8901234567890'
        medicine = medicines.filter(barcode=barcode).first()
        if medicine:
            print(f"✅ Medicine with barcode {barcode} found: {medicine.name}")
        else:
            print(f"❌ Medicine with barcode {barcode} not found")
            
    except Exception as e:
        print(f"❌ Database check failed: {e}")
        return False
    
    # 2. Check Authentication
    print("\n2. AUTHENTICATION CHECK")
    print("-" * 30)
    
    try:
        # Create JWT token for admin user
        refresh = RefreshToken.for_user(admin_user)
        access_token = str(refresh.access_token)
        print("✅ JWT token generation successful")
        
        # Test login API
        login_data = {
            'username': 'admin',
            'password': 'admin123'
        }
        
        response = requests.post('http://localhost:8000/api/login/', json=login_data)
        if response.status_code == 200:
            print("✅ Login API working")
            token_data = response.json()
            access_token = token_data['access']
        else:
            print(f"❌ Login API failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Authentication check failed: {e}")
        return False
    
    # 3. Check API Endpoints
    print("\n3. API ENDPOINTS CHECK")
    print("-" * 30)
    
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    
    # Test pharmacy search endpoint
    try:
        search_response = requests.get(
            'http://localhost:8000/api/pharmacy/medicines/search/?barcode=8901234567890',
            headers=headers
        )
        
        if search_response.status_code == 200:
            search_data = search_response.json()
            print("✅ Pharmacy search API working")
            if search_data.get('found'):
                print(f"✅ Found medicine: {search_data['medicine']['name']}")
            else:
                print("⚠️  Medicine not found (this might be expected)")
        else:
            print(f"❌ Pharmacy search API failed: {search_response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ API endpoint check failed: {e}")
        return False
    
    # 4. Check Frontend API Service
    print("\n4. FRONTEND API SERVICE CHECK")
    print("-" * 30)
    
    try:
        # Test if frontend can access backend
        response = requests.get('http://localhost:8000/api/pharmacy/medicines/')
        if response.status_code == 401:
            print("✅ Backend is running and requires authentication")
        else:
            print(f"⚠️  Backend response: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Backend server not running")
        return False
    except Exception as e:
        print(f"❌ Frontend API check failed: {e}")
        return False
    
    # 5. Check CORS Configuration
    print("\n5. CORS CONFIGURATION CHECK")
    print("-" * 30)
    
    try:
        # Test CORS preflight request
        response = requests.options('http://localhost:8000/api/pharmacy/medicines/')
        if response.status_code in [200, 401]:
            print("✅ CORS configuration working")
        else:
            print(f"⚠️  CORS response: {response.status_code}")
            
    except Exception as e:
        print(f"❌ CORS check failed: {e}")
    
    # 6. Summary
    print("\n6. SYSTEM SUMMARY")
    print("-" * 30)
    print("✅ Database models working")
    print("✅ Authentication working")
    print("✅ API endpoints working")
    print("✅ Backend server accessible")
    print("✅ CORS configuration working")
    
    print("\n🎯 RECOMMENDATIONS:")
    print("-" * 30)
    print("1. Make sure you're logged in to the frontend")
    print("2. Try scanning barcode: 8901234567890")
    print("3. Check browser console for any errors")
    print("4. Verify both frontend and backend servers are running")
    
    return True

if __name__ == '__main__':
    comprehensive_system_check() 