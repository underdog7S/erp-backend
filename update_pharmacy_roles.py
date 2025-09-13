#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings')
django.setup()

from api.models.user import Role, UserProfile, Tenant

def update_pharmacy_roles():
    print("=== Adding Pharmacy-Specific Roles ===")
    
    # Pharmacy-specific roles
    pharmacy_roles = [
        {
            'name': 'pharmacy_admin',
            'description': 'Pharmacy Administrator - Full access to pharmacy management'
        },
        {
            'name': 'pharmacist',
            'description': 'Pharmacist - Can manage medicines, prescriptions, and sales'
        },
        {
            'name': 'pharmacy_staff',
            'description': 'Pharmacy Staff - Basic pharmacy operations'
        },
        {
            'name': 'pharmacy_cashier',
            'description': 'Pharmacy Cashier - Handle sales and billing'
        },
        {
            'name': 'pharmacy_manager',
            'description': 'Pharmacy Manager - Manage inventory and staff'
        },
        {
            'name': 'pharmacy_assistant',
            'description': 'Pharmacy Assistant - Support pharmacy operations'
        }
    ]
    
    # Create pharmacy roles
    for role_data in pharmacy_roles:
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
    
    print("\n=== Pharmacy Tenant Users ===")
    pharmacy_tenants = Tenant.objects.filter(industry='pharmacy')
    for tenant in pharmacy_tenants:
        print(f"\nTenant: {tenant.name} ({tenant.industry})")
        users = UserProfile.objects.filter(tenant=tenant)
        for user in users:
            print(f"  - {user.user.username}: {user.role.name if user.role else 'No Role'}")

if __name__ == "__main__":
    update_pharmacy_roles() 