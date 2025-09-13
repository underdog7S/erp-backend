#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings')
django.setup()

from api.models.user import UserProfile
from api.models.plan import Plan

def check_user_plan():
    print("=== User Plan Check ===")
    
    # Get all users
    users = UserProfile.objects.all()
    
    for user in users:
        print(f"\nUser: {user.user.username}")
        print(f"Tenant: {user.tenant.name}")
        print(f"Current Plan: {user.tenant.plan.name if user.tenant.plan else 'None'}")
        
        if user.tenant.plan:
            plan = user.tenant.plan
            print(f"Plan Features:")
            print(f"  - has_education: {plan.has_education}")
            print(f"  - has_pharmacy: {plan.has_pharmacy}")
            print(f"  - has_retail: {plan.has_retail}")
            print(f"  - has_healthcare: {plan.has_healthcare}")
        else:
            print("  No plan assigned!")
    
    print("\n=== Available Plans ===")
    plans = Plan.objects.all()
    for plan in plans:
        print(f"\nPlan: {plan.name}")
        print(f"  - has_education: {plan.has_education}")
        print(f"  - has_pharmacy: {plan.has_pharmacy}")
        print(f"  - has_retail: {plan.has_retail}")
        print(f"  - has_healthcare: {plan.has_healthcare}")

if __name__ == "__main__":
    check_user_plan() 