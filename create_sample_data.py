#!/usr/bin/env python
import os
import sys
import django
from django.utils import timezone
from datetime import date, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings')
django.setup()

from api.models.user import UserProfile, Tenant, Role
from pharmacy.models import Medicine, MedicineCategory, Supplier, MedicineBatch, Customer, Sale, SaleItem, Prescription
from django.contrib.auth.models import User

def create_sample_pharmacy_data():
    print("=== Creating Sample Pharmacy Data ===")
    
    # Get pharmacy tenant
    try:
        tenant = Tenant.objects.filter(industry__iexact='pharmacy').first()
        if not tenant:
            print("❌ No pharmacy tenant found. Please create a pharmacy tenant first.")
            return
        
        print(f"✅ Using tenant: {tenant.name}")
        
        # Get pharmacy roles
        pharmacist_role = Role.objects.filter(name='pharmacist').first()
        if not pharmacist_role:
            print("❌ Pharmacist role not found. Please run update_pharmacy_roles.py first.")
            return
        
        # Create medicine categories
        categories = [
            {'name': 'Pain Relief', 'description': 'Medicines for pain and fever'},
            {'name': 'Antibiotic', 'description': 'Antibacterial medications'},
            {'name': 'Antacid', 'description': 'For acid reflux and ulcers'},
            {'name': 'Antiallergic', 'description': 'For allergies and hay fever'}
        ]
        
        print("📂 Creating medicine categories...")
        created_categories = {}
        for cat_data in categories:
            category, created = MedicineCategory.objects.get_or_create(
                name=cat_data['name'],
                tenant=tenant,
                defaults=cat_data
            )
            if created:
                print(f"✅ Created category: {category.name}")
            else:
                print(f"ℹ️  Already exists: {category.name}")
            created_categories[cat_data['name']] = category
        
        # Create suppliers
        suppliers = [
            {
                'name': 'ABC Pharmaceuticals',
                'contact_person': 'John Supplier',
                'phone': '+91 98765 43220',
                'email': 'john@abcpharma.com',
                'address': '123 Pharma Street, City',
                'gst_number': 'GST123456789'
            },
            {
                'name': 'XYZ Pharma',
                'contact_person': 'Jane Supplier',
                'phone': '+91 98765 43221',
                'email': 'jane@xyzpharma.com',
                'address': '456 Medicine Road, Town',
                'gst_number': 'GST987654321'
            }
        ]
        
        print("🏢 Creating suppliers...")
        created_suppliers = []
        for sup_data in suppliers:
            supplier, created = Supplier.objects.get_or_create(
                name=sup_data['name'],
                tenant=tenant,
                defaults=sup_data
            )
            if created:
                print(f"✅ Created supplier: {supplier.name}")
            else:
                print(f"ℹ️  Already exists: {supplier.name}")
            created_suppliers.append(supplier)
        
        # Create sample medicines
        medicines = [
            {
                'name': 'Paracetamol 500mg',
                'generic_name': 'Acetaminophen',
                'category': created_categories['Pain Relief'],
                'manufacturer': 'ABC Pharmaceuticals',
                'strength': '500mg',
                'dosage_form': 'TABLET',
                'prescription_required': False,
                'description': 'Used for fever and pain relief',
                'side_effects': 'Rare side effects include nausea',
                'storage_conditions': 'Store in a cool, dry place'
            },
            {
                'name': 'Amoxicillin 250mg',
                'generic_name': 'Amoxicillin',
                'category': created_categories['Antibiotic'],
                'manufacturer': 'XYZ Pharma',
                'strength': '250mg',
                'dosage_form': 'CAPSULE',
                'prescription_required': True,
                'description': 'Broad spectrum antibiotic',
                'side_effects': 'May cause stomach upset',
                'storage_conditions': 'Store in refrigerator'
            },
            {
                'name': 'Omeprazole 20mg',
                'generic_name': 'Omeprazole',
                'category': created_categories['Antacid'],
                'manufacturer': 'DEF Pharmaceuticals',
                'strength': '20mg',
                'dosage_form': 'CAPSULE',
                'prescription_required': False,
                'description': 'For acid reflux and ulcers',
                'side_effects': 'May cause headache',
                'storage_conditions': 'Store at room temperature'
            },
            {
                'name': 'Cetirizine 10mg',
                'generic_name': 'Cetirizine',
                'category': created_categories['Antiallergic'],
                'manufacturer': 'GHI Pharma',
                'strength': '10mg',
                'dosage_form': 'TABLET',
                'prescription_required': False,
                'description': 'For allergies and hay fever',
                'side_effects': 'May cause drowsiness',
                'storage_conditions': 'Store in a cool, dry place'
            }
        ]
        
        print("📦 Creating medicines...")
        created_medicines = []
        for med_data in medicines:
            medicine, created = Medicine.objects.get_or_create(
                name=med_data['name'],
                tenant=tenant,
                defaults=med_data
            )
            if created:
                print(f"✅ Created: {medicine.name}")
            else:
                print(f"ℹ️  Already exists: {medicine.name}")
            created_medicines.append(medicine)
        
        # Create medicine batches
        print("📦 Creating medicine batches...")
        created_batches = []
        for i, medicine in enumerate(created_medicines):
            supplier = created_suppliers[i % len(created_suppliers)]
            batch_data = {
                'medicine': medicine,
                'tenant': tenant,
                'batch_number': f'BATCH00{i+1}',
                'supplier': supplier,
                'manufacturing_date': date.today() - timedelta(days=30),
                'expiry_date': date.today() + timedelta(days=365),
                'cost_price': 3.00 + (i * 2),
                'selling_price': 5.00 + (i * 3),
                'mrp': 8.00 + (i * 4),
                'quantity_received': 200 - (i * 20),
                'quantity_available': 150 - (i * 15),
                'location': 'Shelf A'
            }
            
            batch, created = MedicineBatch.objects.get_or_create(
                medicine=medicine,
                batch_number=batch_data['batch_number'],
                tenant=tenant,
                defaults=batch_data
            )
            if created:
                print(f"✅ Created batch: {batch.batch_number} for {medicine.name}")
            else:
                print(f"ℹ️  Already exists: {batch.batch_number} for {medicine.name}")
            created_batches.append(batch)
        
        # Create sample customers
        customers = [
            {
                'name': 'John Doe',
                'phone': '+91 98765 43210',
                'email': 'john.doe@email.com',
                'address': '123 Main Street, City',
                'date_of_birth': date(1985, 5, 15)
            },
            {
                'name': 'Jane Smith',
                'phone': '+91 98765 43211',
                'email': 'jane.smith@email.com',
                'address': '456 Oak Avenue, Town',
                'date_of_birth': date(1990, 8, 22)
            },
            {
                'name': 'Mike Johnson',
                'phone': '+91 98765 43212',
                'email': 'mike.johnson@email.com',
                'address': '789 Pine Road, Village',
                'date_of_birth': date(1978, 12, 10)
            }
        ]
        
        print("👥 Creating customers...")
        created_customers = []
        for cust_data in customers:
            customer, created = Customer.objects.get_or_create(
                name=cust_data['name'],
                tenant=tenant,
                defaults=cust_data
            )
            if created:
                print(f"✅ Created: {customer.name}")
            else:
                print(f"ℹ️  Already exists: {customer.name}")
            created_customers.append(customer)
        
        # Create sample sales
        print("💰 Creating sales...")
        for i, customer in enumerate(created_customers):
            sale = Sale.objects.create(
                customer=customer,
                tenant=tenant,
                invoice_number=f'INV{tenant.id:03d}{i+1:03d}',
                sale_date=timezone.now() - timedelta(days=i),
                subtotal=0,
                tax_amount=0,
                discount_amount=0,
                total_amount=0,
                payment_method='CASH',
                payment_status='PAID'
            )
            
            # Add medicine items to sale
            batch = created_batches[i % len(created_batches)]
            quantity = (i + 1) * 2
            unit_price = batch.selling_price
            total_price = quantity * unit_price
            
            SaleItem.objects.create(
                sale=sale,
                medicine_batch=batch,
                tenant=tenant,
                quantity=quantity,
                unit_price=unit_price,
                total_price=total_price
            )
            
            # Update sale total
            sale.subtotal = total_price
            sale.total_amount = total_price
            sale.save()
            
            print(f"✅ Created sale: {customer.name} - ₹{total_price}")
        
        # Create sample prescriptions
        print("📋 Creating prescriptions...")
        for i, customer in enumerate(created_customers):
            prescription = Prescription.objects.create(
                customer=customer,
                tenant=tenant,
                doctor_name=f'Dr. Smith {i+1}',
                prescription_date=timezone.now().date() - timedelta(days=i*2),
                diagnosis=f'Diagnosis {i+1}',
                notes=f'Prescription notes for {customer.name}'
            )
            print(f"✅ Created prescription: RX00{i+1} for {customer.name}")
        
        print("\n=== Sample Data Summary ===")
        print(f"📦 Medicines: {Medicine.objects.filter(tenant=tenant).count()}")
        print(f"📦 Batches: {MedicineBatch.objects.filter(tenant=tenant).count()}")
        print(f"👥 Customers: {Customer.objects.filter(tenant=tenant).count()}")
        print(f"💰 Sales: {Sale.objects.filter(tenant=tenant).count()}")
        print(f"📋 Prescriptions: {Prescription.objects.filter(tenant=tenant).count()}")
        
        print("\n✅ Sample pharmacy data created successfully!")
        print("🎯 You can now refresh the Pharmacy Dashboard to see the data.")
        
    except Exception as e:
        print(f"❌ Error creating sample data: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_sample_pharmacy_data() 