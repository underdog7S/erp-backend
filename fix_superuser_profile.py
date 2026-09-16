import os
import django
import sys

# Set up Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings')
django.setup()

from django.contrib.auth.models import User
from api.models.user import UserProfile, Tenant, Role

def fix_superuser_profile():
    superusers = User.objects.filter(is_superuser=True)
    
    if not superusers.exists():
        print("No superusers found.")
        return

    # Ensure there is a default tenant
    tenant, created = Tenant.objects.get_or_create(
        name="Default System Tenant",
        defaults={"industry": "retail"}
    )
    if created:
        print("Created default tenant.")

    admin_role, _ = Role.objects.get_or_create(name='admin', defaults={'description': 'System Administrator'})

    for su in superusers:
        if not hasattr(su, 'userprofile'):
            profile = UserProfile.objects.create(
                user=su,
                tenant=tenant,
                role=admin_role,
                phone='0000000000'
            )
            print(f"Created UserProfile for superuser: {su.username}")
        else:
            print(f"Superuser {su.username} already has a UserProfile.")

if __name__ == '__main__':
    fix_superuser_profile()
