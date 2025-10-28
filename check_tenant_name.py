#!/usr/bin/env python
"""
Script to check current tenant name(s) in the database
Run: python manage.py shell < check_tenant_name.py
Or: python check_tenant_name.py (if Django is set up)
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings')
django.setup()

from api.models.user import Tenant, UserProfile

def check_tenants():
    """Check all tenants in the database"""
    print("=" * 60)
    print("TENANT INFORMATION")
    print("=" * 60)
    
    tenants = Tenant.objects.all()
    
    if not tenants.exists():
        print("No tenants found in database.")
        return
    
    print(f"\nTotal Tenants: {tenants.count()}\n")
    
    for i, tenant in enumerate(tenants, 1):
        print(f"{i}. Tenant ID: {tenant.id}")
        print(f"   Name: {tenant.name}")
        print(f"   Industry: {tenant.industry}")
        print(f"   Slug: {tenant.slug}")
        print(f"   Plan: {tenant.plan.name if tenant.plan else 'None'}")
        
        # Count users in this tenant
        user_count = UserProfile.objects.filter(tenant=tenant).count()
        print(f"   Users: {user_count}")
        
        print("-" * 60)
    
    # Check if AdminKVMS exists
    adminkvms = Tenant.objects.filter(name__icontains='AdminKVMS')
    if adminkvms.exists():
        print("\n⚠️  WARNING: Found tenant(s) with 'AdminKVMS' in name:")
        for tenant in adminkvms:
            print(f"   - ID {tenant.id}: {tenant.name}")

if __name__ == '__main__':
    check_tenants()

