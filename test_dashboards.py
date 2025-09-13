#!/usr/bin/env python
import os
import sys
import django
import requests
from datetime import date

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings')
django.setup()

from api.models.user import Tenant
from pharmacy.models import Medicine, MedicineBatch, Customer, Sale, Prescription
from education.models import Student, Class, FeeStructure, FeePayment, Attendance, ReportCard
from retail.models import Product, Customer as RetailCustomer, Sale as RetailSale

def test_dashboards():
    print("=== Testing All Dashboards ===")
    
    # Test Pharmacy Dashboard
    print("\n🏥 Testing Pharmacy Dashboard...")
    pharmacy_tenant = Tenant.objects.filter(industry__iexact='pharmacy').first()
    if pharmacy_tenant:
        medicines = Medicine.objects.filter(tenant=pharmacy_tenant).count()
        batches = MedicineBatch.objects.filter(tenant=pharmacy_tenant).count()
        customers = Customer.objects.filter(tenant=pharmacy_tenant).count()
        sales = Sale.objects.filter(tenant=pharmacy_tenant).count()
        prescriptions = Prescription.objects.filter(tenant=pharmacy_tenant).count()
        
        print(f"✅ Pharmacy Data:")
        print(f"  - Medicines: {medicines}")
        print(f"  - Batches: {batches}")
        print(f"  - Customers: {customers}")
        print(f"  - Sales: {sales}")
        print(f"  - Prescriptions: {prescriptions}")
    else:
        print("❌ No pharmacy tenant found")
    
    # Test Education Dashboard
    print("\n🎓 Testing Education Dashboard...")
    education_tenant = Tenant.objects.filter(industry__iexact='education').first()
    if education_tenant:
        students = Student.objects.filter(tenant=education_tenant).count()
        classes = Class.objects.filter(tenant=education_tenant).count()
        fee_structures = FeeStructure.objects.filter(tenant=education_tenant).count()
        fee_payments = FeePayment.objects.filter(tenant=education_tenant).count()
        attendance = Attendance.objects.filter(tenant=education_tenant).count()
        report_cards = ReportCard.objects.filter(tenant=education_tenant).count()
        
        print(f"✅ Education Data:")
        print(f"  - Students: {students}")
        print(f"  - Classes: {classes}")
        print(f"  - Fee Structures: {fee_structures}")
        print(f"  - Fee Payments: {fee_payments}")
        print(f"  - Attendance Records: {attendance}")
        print(f"  - Report Cards: {report_cards}")
    else:
        print("❌ No education tenant found")
    
    # Test Retail Dashboard
    print("\n🛒 Testing Retail Dashboard...")
    retail_tenant = Tenant.objects.filter(industry__iexact='retail').first()
    if retail_tenant:
        products = Product.objects.filter(tenant=retail_tenant).count()
        customers = RetailCustomer.objects.filter(tenant=retail_tenant).count()
        sales = RetailSale.objects.filter(tenant=retail_tenant).count()
        
        print(f"✅ Retail Data:")
        print(f"  - Products: {products}")
        print(f"  - Customers: {customers}")
        print(f"  - Sales: {sales}")
    else:
        print("❌ No retail tenant found")
    
    # Test API Endpoints
    print("\n🌐 Testing API Endpoints...")
    base_url = "http://127.0.0.1:8000"
    
    try:
        # Test Pharmacy Analytics
        response = requests.get(f"{base_url}/api/pharmacy/analytics/")
        if response.status_code == 200:
            print("✅ Pharmacy Analytics API: Working")
        else:
            print(f"❌ Pharmacy Analytics API: {response.status_code}")
    except:
        print("❌ Pharmacy Analytics API: Connection failed")
    
    try:
        # Test Education Analytics
        response = requests.get(f"{base_url}/api/education/analytics/")
        if response.status_code == 200:
            print("✅ Education Analytics API: Working")
        else:
            print(f"❌ Education Analytics API: {response.status_code}")
    except:
        print("❌ Education Analytics API: Connection failed")
    
    try:
        # Test Retail Analytics
        response = requests.get(f"{base_url}/api/retail/analytics/")
        if response.status_code == 200:
            print("✅ Retail Analytics API: Working")
        else:
            print(f"❌ Retail Analytics API: {response.status_code}")
    except:
        print("❌ Retail Analytics API: Connection failed")
    
    print("\n=== Dashboard Test Complete ===")
    print("🎯 All dashboards should now display real data!")
    print("📊 Check the frontend at http://localhost:3000 to see the dashboards in action.")

if __name__ == "__main__":
    test_dashboards() 