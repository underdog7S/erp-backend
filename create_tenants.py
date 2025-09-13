#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings')
django.setup()

from api.models.user import Tenant
from api.models.plan import Plan

def create_tenants():
    print("=== Creating Missing Tenants ===")
    
    # Get the Free plan
    free_plan = Plan.objects.filter(name__iexact='Free').first()
    if not free_plan:
        print("❌ Free plan not found. Please run setup_plans first.")
        return
    
    # Define tenants to create
    tenants_data = [
        {
            'name': 'Pharmacy Store',
            'industry': 'pharmacy'
        },
        {
            'name': 'Retail Store',
            'industry': 'retail'
        },
        {
            'name': 'Education Institute',
            'industry': 'education'
        }
    ]
    
    for tenant_data in tenants_data:
        tenant, created = Tenant.objects.get_or_create(
            name=tenant_data['name'],
            defaults={
                'industry': tenant_data['industry'],
                'plan': free_plan
            }
        )
        
        if created:
            print(f"✅ Created tenant: {tenant.name} ({tenant.industry})")
        else:
            print(f"ℹ️  Already exists: {tenant.name} ({tenant.industry})")
    
    print("\n=== Tenant Creation Complete ===")
    print("🎯 You can now run the sample data scripts for each industry.")

if __name__ == "__main__":
    create_tenants() 