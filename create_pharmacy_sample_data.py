#!/usr/bin/env python
import os
import sys
import django
from datetime import date, timedelta

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings')
django.setup()

from django.contrib.auth.models import User
from api.models.user import Tenant, UserProfile, Role
from pharmacy.models import MedicineCategory, Supplier, Medicine, MedicineBatch

def create_sample_pharmacy_data():
    """Create sample pharmacy data with barcodes for testing"""
    
    # Get or create a tenant
    tenant, created = Tenant.objects.get_or_create(
        name="Test Pharmacy",
        defaults={
            'industry': 'healthcare',
            'storage_used_mb': 0
        }
    )
    print(f"Tenant: {tenant.name}")
    
    # Create or get admin role
    admin_role, created = Role.objects.get_or_create(
        name='Admin',
        defaults={'description': 'Administrator role'}
    )
    print(f"Role: {admin_role.name}")
    
    # Create or get admin user
    admin_user, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@testpharmacy.com',
            'first_name': 'Admin',
            'last_name': 'User',
            'is_staff': True,
            'is_superuser': True
        }
    )
    if created:
        admin_user.set_password('admin123')
        admin_user.save()
    print(f"User: {admin_user.username}")
    
    # Get or create a user profile
    user_profile, created = UserProfile.objects.get_or_create(
        user=admin_user,
        defaults={
            'tenant': tenant,
            'role': admin_role
        }
    )
    print(f"User Profile: {user_profile.user.username}")
    
    # Create medicine categories
    categories = {
        'Pain Relief': 'Medicines for pain and fever',
        'Antibiotics': 'Antibacterial medications',
        'Vitamins': 'Vitamin and mineral supplements',
        'Cough & Cold': 'Medicines for respiratory issues',
        'Digestive Health': 'Medicines for stomach and digestive issues'
    }
    
    created_categories = {}
    for name, description in categories.items():
        category, created = MedicineCategory.objects.get_or_create(
            name=name,
            tenant=tenant,
            defaults={'description': description}
        )
        created_categories[name] = category
        print(f"Category: {category.name}")
    
    # Create suppliers
    suppliers = {
        'ABC Pharmaceuticals': 'Leading pharmaceutical manufacturer',
        'XYZ Pharma Ltd': 'Generic medicine supplier',
        'HealthCare Solutions': 'Premium medicine supplier',
        'Kissan Foods': 'Food products manufacturer'
    }
    
    created_suppliers = {}
    for name, description in suppliers.items():
        supplier, created = Supplier.objects.get_or_create(
            name=name,
            tenant=tenant,
            defaults={
                'contact_person': 'John Doe',
                'phone': '1234567890',
                'email': f'contact@{name.lower().replace(" ", "")}.com',
                'address': f'123 Main St, {name}',
                'gst_number': 'GST123456789',
                'payment_terms': 'Net 30'
            }
        )
        created_suppliers[name] = supplier
        print(f"Supplier: {supplier.name}")
    
    # Create medicines with barcodes
    medicines_data = [
        {
            'name': 'Paracetamol 500mg',
            'generic_name': 'Acetaminophen',
            'category': 'Pain Relief',
            'manufacturer': 'ABC Pharmaceuticals',
            'strength': '500mg',
            'dosage_form': 'TABLET',
            'description': 'Fever and pain relief',
            'barcode': '1234567890123',
            'unit_price': '10.50'
        },
        {
            'name': 'Amoxicillin 250mg',
            'generic_name': 'Amoxicillin',
            'category': 'Antibiotics',
            'manufacturer': 'XYZ Pharma Ltd',
            'strength': '250mg',
            'dosage_form': 'CAPSULE',
            'description': 'Antibiotic for bacterial infections',
            'barcode': '2345678901234',
            'unit_price': '15.00'
        },
        {
            'name': 'Vitamin C 1000mg',
            'generic_name': 'Ascorbic Acid',
            'category': 'Vitamins',
            'manufacturer': 'HealthCare Solutions',
            'strength': '1000mg',
            'dosage_form': 'TABLET',
            'description': 'Vitamin C supplement for immunity',
            'barcode': '3456789012345',
            'unit_price': '25.00'
        },
        {
            'name': 'Omeprazole 20mg',
            'generic_name': 'Omeprazole',
            'category': 'Digestive Health',
            'manufacturer': 'ABC Pharmaceuticals',
            'strength': '20mg',
            'dosage_form': 'CAPSULE',
            'description': 'Acid reflux and stomach ulcer treatment',
            'barcode': '4567890123456',
            'unit_price': '30.00'
        },
        {
            'name': 'Cetirizine 10mg',
            'generic_name': 'Cetirizine',
            'category': 'Cough & Cold',
            'manufacturer': 'XYZ Pharma Ltd',
            'strength': '10mg',
            'dosage_form': 'TABLET',
            'description': 'Antihistamine for allergies',
            'barcode': '5678901234567',
            'unit_price': '12.00'
        },
        {
            'name': 'Kissan Peanut Butter',
            'generic_name': 'Peanut Butter',
            'category': 'Vitamins',
            'manufacturer': 'Kissan Foods',
            'strength': '500g',
            'dosage_form': 'OTHER',
            'description': 'Nutritious peanut butter spread',
            'barcode': '8901234567890',
            'unit_price': '150.00'
        }
    ]
    
    created_medicines = {}
    for medicine_data in medicines_data:
        medicine, created = Medicine.objects.get_or_create(
            name=medicine_data['name'],
            tenant=tenant,
            defaults={
                'generic_name': medicine_data['generic_name'],
                'category': created_categories[medicine_data['category']],
                'manufacturer': medicine_data['manufacturer'],
                'strength': medicine_data['strength'],
                'dosage_form': medicine_data['dosage_form'],
                'description': medicine_data['description'],
                'barcode': medicine_data['barcode'],
                'prescription_required': False
            }
        )
        created_medicines[medicine_data['name']] = medicine
        print(f"Medicine: {medicine.name} (Barcode: {medicine.barcode})")
    
    # Create medicine batches
    for medicine_name, medicine in created_medicines.items():
        medicine_data = next(m for m in medicines_data if m['name'] == medicine_name)
        supplier_name = medicine_data['manufacturer']
        supplier = created_suppliers[supplier_name]
        
        batch, created = MedicineBatch.objects.get_or_create(
            medicine=medicine,
            batch_number=f"BATCH{medicine.id:03d}",
            tenant=tenant,
            defaults={
                'supplier': supplier,
                'manufacturing_date': date.today() - timedelta(days=30),
                'expiry_date': date.today() + timedelta(days=365),
                'cost_price': float(medicine_data['unit_price']) * 0.7,
                'selling_price': float(medicine_data['unit_price']),
                'mrp': float(medicine_data['unit_price']) * 1.2,
                'quantity_received': 100,
                'quantity_available': 100,
                'location': 'Main Store'
            }
        )
        print(f"Batch: {batch.batch_number} for {medicine.name}")
    
    print("\n✅ Sample pharmacy data created successfully!")
    print("\n📋 Test Barcodes:")
    for medicine_data in medicines_data:
        print(f"  • {medicine_data['name']}: {medicine_data['barcode']}")

if __name__ == '__main__':
    create_sample_pharmacy_data() 