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
from retail.models import Product, ProductCategory, Supplier, Customer, Sale, SaleItem, StockTransfer, Warehouse, Inventory, StockTransferItem
from django.contrib.auth.models import User

def create_sample_retail_data():
    print("=== Creating Sample Retail Data ===")
    
    try:
        tenant = Tenant.objects.filter(industry__iexact='retail').first()
        if not tenant:
            print("❌ No retail tenant found. Please create a retail tenant first.")
            return
        
        print(f"✅ Using tenant: {tenant.name}")
        
        # Create categories
        categories = [
            'Electronics',
            'Clothing',
            'Home & Garden',
            'Sports & Outdoors'
        ]
        
        print("📂 Creating categories...")
        created_categories = []
        for cat_name in categories:
            category, created = ProductCategory.objects.get_or_create(
                name=cat_name,
                tenant=tenant
            )
            if created:
                print(f"✅ Created category: {category.name}")
            else:
                print(f"ℹ️  Already exists: {category.name}")
            created_categories.append(category)
        
        # Create suppliers
        suppliers = [
            {
                'name': 'ABC Electronics',
                'contact_person': 'John Supplier',
                'phone': '+91 98765 43220',
                'email': 'john@abcelectronics.com',
                'address': '123 Electronics Street, City',
                'gst_number': 'GST123456789'
            },
            {
                'name': 'XYZ Clothing',
                'contact_person': 'Jane Supplier',
                'phone': '+91 98765 43221',
                'email': 'jane@xyzclothing.com',
                'address': '456 Clothing Road, Town',
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
        
        # Create warehouses
        warehouses = [
            {
                'name': 'Main Warehouse',
                'address': '123 Warehouse Street, City',
                'contact_person': 'Warehouse Manager',
                'phone': '+91 98765 43230',
                'is_primary': True
            },
            {
                'name': 'Store Warehouse',
                'address': '456 Store Road, Town',
                'contact_person': 'Store Manager',
                'phone': '+91 98765 43231',
                'is_primary': False
            }
        ]
        
        print("🏪 Creating warehouses...")
        created_warehouses = []
        for wh_data in warehouses:
            warehouse, created = Warehouse.objects.get_or_create(
                name=wh_data['name'],
                tenant=tenant,
                defaults=wh_data
            )
            if created:
                print(f"✅ Created warehouse: {warehouse.name}")
            else:
                print(f"ℹ️  Already exists: {warehouse.name}")
            created_warehouses.append(warehouse)
        
        # Create products
        products = [
            {
                'name': 'Smartphone X1',
                'category': created_categories[0],
                'sku': 'PHONE001',
                'description': 'Latest smartphone with advanced features',
                'brand': 'TechCorp',
                'unit_of_measure': 'PCS',
                'cost_price': 12000.00,
                'selling_price': 15000.00,
                'mrp': 16000.00,
                'reorder_level': 10,
                'max_stock_level': 100
            },
            {
                'name': 'Laptop Pro',
                'category': created_categories[0],
                'sku': 'LAPTOP001',
                'description': 'Professional laptop for work and gaming',
                'brand': 'TechCorp',
                'unit_of_measure': 'PCS',
                'cost_price': 38000.00,
                'selling_price': 45000.00,
                'mrp': 48000.00,
                'reorder_level': 5,
                'max_stock_level': 50
            },
            {
                'name': 'Cotton T-Shirt',
                'category': created_categories[1],
                'sku': 'TSHIRT001',
                'description': 'Comfortable cotton t-shirt',
                'brand': 'FashionBrand',
                'unit_of_measure': 'PCS',
                'cost_price': 300.00,
                'selling_price': 500.00,
                'mrp': 600.00,
                'reorder_level': 20,
                'max_stock_level': 200
            },
            {
                'name': 'Running Shoes',
                'category': created_categories[3],
                'sku': 'SHOES001',
                'description': 'Professional running shoes',
                'brand': 'SportBrand',
                'unit_of_measure': 'PCS',
                'cost_price': 1800.00,
                'selling_price': 2500.00,
                'mrp': 2800.00,
                'reorder_level': 8,
                'max_stock_level': 80
            }
        ]
        
        print("📦 Creating products...")
        created_products = []
        for prod_data in products:
            product, created = Product.objects.get_or_create(
                sku=prod_data['sku'],
                tenant=tenant,
                defaults=prod_data
            )
            if created:
                print(f"✅ Created product: {product.name}")
            else:
                print(f"ℹ️  Already exists: {product.name}")
            created_products.append(product)
        
        # Create customers
        customers = [
            {
                'name': 'John Customer',
                'phone': '+91 98765 43210',
                'email': 'john.customer@email.com',
                'address': '123 Customer Street, City'
            },
            {
                'name': 'Jane Customer',
                'phone': '+91 98765 43211',
                'email': 'jane.customer@email.com',
                'address': '456 Customer Avenue, Town'
            },
            {
                'name': 'Mike Customer',
                'phone': '+91 98765 43212',
                'email': 'mike.customer@email.com',
                'address': '789 Customer Road, Village'
            }
        ]
        
        print("👥 Creating customers...")
        created_customers = []
        for cust_data in customers:
            customer, created = Customer.objects.get_or_create(
                email=cust_data['email'],
                tenant=tenant,
                defaults=cust_data
            )
            if created:
                print(f"✅ Created customer: {customer.name}")
            else:
                print(f"ℹ️  Already exists: {customer.name}")
            created_customers.append(customer)
        
        # Create sales
        print("💰 Creating sales...")
        for i, customer in enumerate(created_customers):
            warehouse = created_warehouses[i % len(created_warehouses)]
            sale = Sale.objects.create(
                customer=customer,
                tenant=tenant,
                warehouse=warehouse,
                invoice_number=f'INV{tenant.id:03d}{i+1:03d}',
                sale_date=timezone.now() - timedelta(days=i),
                subtotal=0,
                tax_amount=0,
                discount_amount=0,
                total_amount=0,
                payment_method='CASH',
                payment_status='PAID'
            )
            
            # Add product items to sale
            product = created_products[i % len(created_products)]
            quantity = (i + 1) * 2
            unit_price = product.selling_price
            total_price = quantity * unit_price
            
            SaleItem.objects.create(
                sale=sale,
                product=product,
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
        
        # Create stock transfers
        print("🚚 Creating stock transfers...")
        for i, product in enumerate(created_products):
            from_warehouse = created_warehouses[0]
            to_warehouse = created_warehouses[1]
            transfer = StockTransfer.objects.create(
                tenant=tenant,
                transfer_number=f'TRF{tenant.id:03d}{i+1:03d}',
                from_warehouse=from_warehouse,
                to_warehouse=to_warehouse,
                transfer_date=timezone.now().date() - timedelta(days=i*2),
                status='COMPLETED',
                notes=f'Regular stock transfer for {product.name}'
            )
            
            # Create stock transfer item
            StockTransferItem.objects.create(
                tenant=tenant,
                stock_transfer=transfer,
                product=product,
                quantity=10 + (i * 5)
            )
            
            print(f"✅ Created transfer: {product.name} - {transfer.transfer_number}")
        
        print("\n=== Sample Retail Data Summary ===")
        print(f"📂 Categories: {ProductCategory.objects.filter(tenant=tenant).count()}")
        print(f"🏢 Suppliers: {Supplier.objects.filter(tenant=tenant).count()}")
        print(f"🏪 Warehouses: {Warehouse.objects.filter(tenant=tenant).count()}")
        print(f"📦 Products: {Product.objects.filter(tenant=tenant).count()}")
        print(f"👥 Customers: {Customer.objects.filter(tenant=tenant).count()}")
        print(f"💰 Sales: {Sale.objects.filter(tenant=tenant).count()}")
        print(f"🚚 Stock Transfers: {StockTransfer.objects.filter(tenant=tenant).count()}")
        
        print("\n✅ Sample retail data created successfully!")
        print("🎯 You can now refresh the Retail Dashboard to see the data.")
        
    except Exception as e:
        print(f"❌ Error creating sample data: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_sample_retail_data() 