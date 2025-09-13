#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings')
django.setup()

from api.models.user import Role

def update_retail_roles():
    print("=== Adding Retail-Specific Roles ===")
    
    # Retail-specific roles
    retail_roles = [
        {
            'name': 'retail_admin',
            'description': 'Retail Administrator - Full access to retail management'
        },
        {
            'name': 'retail_manager',
            'description': 'Retail Manager - Manage inventory, staff, and operations'
        },
        {
            'name': 'retail_staff',
            'description': 'Retail Staff - Basic retail operations'
        },
        {
            'name': 'retail_cashier',
            'description': 'Retail Cashier - Handle sales and billing'
        },
        {
            'name': 'retail_assistant',
            'description': 'Retail Assistant - Support retail operations'
        }
    ]
    
    # Create retail roles
    for role_data in retail_roles:
        role, created = Role.objects.get_or_create(
            name=role_data['name'],
            defaults={'description': role_data['description']}
        )
        if created:
            print(f"✅ Created role: {role.name}")
        else:
            print(f"ℹ️  Role already exists: {role.name}")
    
    print("\n=== Current All Roles ===")
    all_roles = Role.objects.all()
    for role in all_roles:
        print(f"- {role.name}: {role.description}")

if __name__ == "__main__":
    update_retail_roles() 