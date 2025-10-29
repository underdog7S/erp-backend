#!/usr/bin/env python
"""
Create Education Roles Script
Creates all necessary roles for the education module
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings_production')
django.setup()

from api.models.user import Role

def create_education_roles():
    """Create all education-related roles"""
    print("=== Creating Education Roles ===")
    
    education_roles = [
        {
            'name': 'admin',
            'description': 'Administrator - Full system access'
        },
        {
            'name': 'principal',
            'description': 'Principal - School administration access'
        },
        {
            'name': 'teacher',
            'description': 'Teacher - Can manage classes and students'
        },
        {
            'name': 'staff',
            'description': 'Staff - Basic staff access'
        },
        {
            'name': 'student',
            'description': 'Student - Student access only'
        },
        {
            'name': 'accountant',
            'description': 'Accountant - Financial management access'
        }
    ]
    
    # Create roles
    created_count = 0
    for role_data in education_roles:
        role, created = Role.objects.get_or_create(
            name=role_data['name'],
            defaults={'description': role_data['description']}
        )
        if created:
            print(f"✅ Created role: {role.name}")
            created_count += 1
        else:
            print(f"ℹ️  Role already exists: {role.name}")
    
    print(f"\n✅ Created {created_count} new roles")
    print("\n=== All Available Roles ===")
    all_roles = Role.objects.all().order_by('name')
    for role in all_roles:
        print(f"- {role.name}: {role.description or 'No description'}")

if __name__ == "__main__":
    create_education_roles()

