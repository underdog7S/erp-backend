#!/usr/bin/env python
"""
Script to update tenant name from AdminKVMS to your desired name
Usage: 
    python manage.py shell < update_tenant_name.py
    Or: python update_tenant_name.py

Edit the NEW_NAME variable below before running.
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings')
django.setup()

from api.models.user import Tenant, UserProfile

# ============================================
# EDIT THIS: Set your desired tenant name
# ============================================
NEW_NAME = "Your School Name"  # Change this to your actual school/company name
# ============================================

def update_tenant_name(old_name="AdminKVMS", new_name=None):
    """
    Update tenant name from old_name to new_name
    
    Args:
        old_name: The current tenant name to find and replace (default: "AdminKVMS")
        new_name: The new name to set (default: uses NEW_NAME constant)
    """
    if new_name is None:
        new_name = NEW_NAME
    
    print("=" * 60)
    print("UPDATE TENANT NAME")
    print("=" * 60)
    
    # Find tenant(s) with the old name
    tenants = Tenant.objects.filter(name__icontains=old_name)
    
    if not tenants.exists():
        print(f"\n❌ No tenant found with name containing '{old_name}'")
        print("\nCurrent tenants in database:")
        all_tenants = Tenant.objects.all()
        for tenant in all_tenants:
            print(f"   - ID {tenant.id}: {tenant.name}")
        return
    
    print(f"\nFound {tenants.count()} tenant(s) with '{old_name}' in name:\n")
    
    for tenant in tenants:
        print(f"Tenant ID: {tenant.id}")
        print(f"Current Name: {tenant.name}")
        print(f"Industry: {tenant.industry}")
        print(f"Users: {UserProfile.objects.filter(tenant=tenant).count()}")
        print("-" * 60)
    
    # Confirm update
    print(f"\n⚠️  This will update tenant name(s) to: '{new_name}'")
    print("\nIf you want to proceed, uncomment the update code below.")
    print("Or use Django shell to update manually:\n")
    print("  python manage.py shell")
    print("  >>> from api.models.user import Tenant")
    print("  >>> tenant = Tenant.objects.get(id=1)  # Replace 1 with your tenant ID")
    print(f"  >>> tenant.name = '{new_name}'")
    print("  >>> tenant.save()")
    
    # Uncomment below to actually update:
    """
    # Update all matching tenants
    updated_count = 0
    for tenant in tenants:
        old_name_value = tenant.name
        tenant.name = new_name
        tenant.save()
        updated_count += 1
        print(f"✅ Updated Tenant ID {tenant.id}: '{old_name_value}' → '{new_name}'")
    
    print(f"\n✅ Successfully updated {updated_count} tenant(s)")
    """

if __name__ == '__main__':
    # You can specify custom names here
    update_tenant_name(old_name="AdminKVMS", new_name=NEW_NAME)

