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

def check_medicines():
    """Check what medicines are in the database"""
    medicines = Medicine.objects.all()
    
    print(f"Total medicines in database: {medicines.count()}")
    print("\nMedicines with barcodes:")
    print("-" * 50)
    
    for medicine in medicines:
        print(f"ID: {medicine.id}")
        print(f"Name: {medicine.name}")
        print(f"Barcode: {medicine.barcode}")
        print(f"Manufacturer: {medicine.manufacturer}")
        print(f"Category: {medicine.category}")
        print("-" * 30)
    
    # Check specific barcodes
    test_barcodes = [
        '1234567890123',
        '2345678901234', 
        '3456789012345',
        '4567890123456',
        '5678901234567',
        '8901234567890'
    ]
    
    print("\nChecking specific barcodes:")
    print("-" * 30)
    
    for barcode in test_barcodes:
        medicine = Medicine.objects.filter(barcode=barcode).first()
        if medicine:
            print(f"✅ Found: {barcode} -> {medicine.name}")
        else:
            print(f"❌ Not found: {barcode}")

if __name__ == '__main__':
    check_medicines() 