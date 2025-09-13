#!/usr/bin/env python
import os
import sys
import django
from django.utils import timezone

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings')
django.setup()

from django.contrib.auth.models import User
from api.models.user import UserProfile

def refresh_user_session():
    print("=== Refreshing User Sessions ===")
    
    # Get all users
    users = UserProfile.objects.all()
    
    for user_profile in users:
        user = user_profile.user
        print(f"\nRefreshing session for user: {user.username}")
        
        # Update last login to force session refresh
        user.last_login = timezone.now()
        user.save()
        
        print(f"  - Updated last_login for {user.username}")
        print(f"  - Tenant: {user_profile.tenant.name}")
        print(f"  - Plan: {user_profile.tenant.plan.name if user_profile.tenant.plan else 'None'}")
        
        if user_profile.tenant.plan:
            plan = user_profile.tenant.plan
            print(f"  - Plan Features:")
            print(f"    * has_education: {plan.has_education}")
            print(f"    * has_pharmacy: {plan.has_pharmacy}")
            print(f"    * has_retail: {plan.has_retail}")
    
    print("\n=== Session Refresh Complete ===")
    print("Users should now log out and log back in to pick up new permissions.")

if __name__ == "__main__":
    refresh_user_session() 