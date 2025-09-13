#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings')
django.setup()

from api.models.user import Tenant
from pharmacy.models import Medicine, MedicineBatch, Customer, Sale, Prescription

def check_pharmacy_data():
    print("=== Checking Pharmacy Data ===")
    
    # Get pharmacy tenant
    tenant = Tenant.objects.filter(industry__iexact='pharmacy').first()
    if not tenant:
        print("❌ No pharmacy tenant found.")
        return
    
    print(f"✅ Using tenant: {tenant.name}")
    
    # Check medicines
    medicines = Medicine.objects.filter(tenant=tenant)
    print(f"📦 Medicines: {medicines.count()}")
    for med in medicines[:3]:  # Show first 3
        print(f"  - {med.name}")
    
    # Check batches
    batches = MedicineBatch.objects.filter(tenant=tenant)
    print(f"📦 Batches: {batches.count()}")
    for batch in batches[:3]:  # Show first 3
        print(f"  - {batch.medicine.name} - {batch.batch_number} (Qty: {batch.quantity_available})")
    
    # Check customers
    customers = Customer.objects.filter(tenant=tenant)
    print(f"👥 Customers: {customers.count()}")
    for cust in customers[:3]:  # Show first 3
        print(f"  - {cust.name}")
    
    # Check sales
    sales = Sale.objects.filter(tenant=tenant)
    print(f"💰 Sales: {sales.count()}")
    for sale in sales[:3]:  # Show first 3
        print(f"  - {sale.invoice_number} - ₹{sale.total_amount}")
    
    # Check prescriptions
    prescriptions = Prescription.objects.filter(tenant=tenant)
    print(f"📋 Prescriptions: {prescriptions.count()}")
    for pres in prescriptions[:3]:  # Show first 3
        print(f"  - {pres.customer.name} - {pres.doctor_name}")
    
    print("\n✅ Pharmacy data check complete!")

if __name__ == "__main__":
    check_pharmacy_data() 