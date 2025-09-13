#!/usr/bin/env python3
"""
Script to create superuser and plans for production deployment
Run this script to set up initial data
"""
import os
import sys
import django

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings_production')

# Setup Django
django.setup()

from django.contrib.auth.models import User
from api.models.plan import Plan

def create_superuser():
    """Create superuser if it doesn't exist"""
    username = 'admin'
    email = 'admin@zenitherp.com'
    password = 'admin123'  # Change this in production
    
    if not User.objects.filter(username=username).exists():
        User.objects.create_superuser(username, email, password)
        print(f"✅ Superuser '{username}' created successfully!")
        print(f"   Username: {username}")
        print(f"   Password: {password}")
        print(f"   Email: {email}")
    else:
        print(f"ℹ️  Superuser '{username}' already exists")

def create_plans():
    """Create default plans if they don't exist"""
    plans_data = [
        {
            'name': 'free',
            'display_name': 'Free',
            'description': 'Basic features for small businesses',
            'price': 0.00,
            'max_users': 5,
            'max_storage_gb': 1,
            'features': {'modules': ['basic_dashboard', 'user_management']}
        },
        {
            'name': 'starter',
            'display_name': 'Starter',
            'description': 'Perfect for growing businesses',
            'price': 29.99,
            'max_users': 25,
            'max_storage_gb': 10,
            'features': {'modules': ['dashboard', 'user_management', 'inventory', 'sales']}
        },
        {
            'name': 'pro',
            'display_name': 'Pro',
            'description': 'Advanced features for established businesses',
            'price': 99.99,
            'max_users': 100,
            'max_storage_gb': 50,
            'features': {'modules': ['dashboard', 'user_management', 'inventory', 'sales', 'analytics', 'integrations']}
        },
        {
            'name': 'enterprise',
            'display_name': 'Enterprise',
            'description': 'Full-featured solution for large organizations',
            'price': 299.99,
            'max_users': 1000,
            'max_storage_gb': 200,
            'features': {'modules': ['all_modules', 'custom_integrations', 'priority_support']}
        }
    ]
    
    for plan_data in plans_data:
        plan, created = Plan.objects.get_or_create(
            name=plan_data['name'],
            defaults=plan_data
        )
        if created:
            print(f"✅ Plan '{plan.display_name}' created successfully!")
        else:
            print(f"ℹ️  Plan '{plan.display_name}' already exists")

def main():
    """Main function to set up initial data"""
    print("🚀 Setting up initial data for Zenith ERP...")
    
    try:
        create_superuser()
        create_plans()
        print("\n🎉 Initial setup completed successfully!")
        print("\n📋 Next steps:")
        print("1. Access admin panel: https://erp-backend-av9v.onrender.com/admin/")
        print("2. Login with username: admin, password: admin123")
        print("3. Change the admin password in Django admin")
        print("4. Test user registration on your frontend")
        
    except Exception as e:
        print(f"❌ Error during setup: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main()
