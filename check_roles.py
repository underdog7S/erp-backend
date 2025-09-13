#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings')
django.setup()

from api.models.user import Role, UserProfile, Tenant

def check_and_update_roles():
    print("=== Current Roles ===")
    roles = Role.objects.all()
    for role in roles:
        print(f"- {role.name}: {role.description}")
    
    print("\n=== Current Tenants ===")
    tenants = Tenant.objects.all()
    for tenant in tenants:
        print(f"- {tenant.name}: {tenant.industry}")
    
    print("\n=== Current Users ===")
    users = UserProfile.objects.all()
    for user in users:
        print(f"- {user.user.username}: {user.role.name if user.role else 'No Role'} in {user.tenant.name} ({user.tenant.industry})")

if __name__ == "__main__":
    check_and_update_roles() 