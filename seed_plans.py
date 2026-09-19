import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings')
django.setup()

from api.models.plan import Plan

def seed_plans():
    print("Deleting old plans...")
    Plan.objects.all().delete()
    
    print("Creating new plans to match the SaaS Strategy...")
    
    Plan.objects.create(
        name="Free",
        description="Perfect for small teams to get started",
        max_users=2,
        storage_limit_mb=500,
        price=0,
        billing_cycle="monthly",
        color="#4caf50",
        popular=False,
        has_dashboard=True,
        has_inventory=True
    )
    
    Plan.objects.create(
        name="Starter",
        description="Ideal for growing businesses",
        max_users=15,
        storage_limit_mb=5120, # 5 GB
        price=2499,
        billing_cycle="year",
        color="#2196f3",
        popular=True,
        has_dashboard=True,
        has_inventory=True,
        has_api_access=True,
        has_priority_support=True
    )
    
    Plan.objects.create(
        name="Pro",
        description="Perfect for established organizations",
        max_users=50,
        storage_limit_mb=20480, # 20 GB
        price=6999,
        billing_cycle="year",
        color="#9c27b0",
        popular=False,
        has_dashboard=True,
        has_inventory=True,
        has_api_access=True,
        has_analytics=True,
        has_white_label=True,
        has_priority_support=True
    )
    
    Plan.objects.create(
        name="Enterprise",
        description="For large scale deployments",
        max_users=None, # Unlimited
        storage_limit_mb=102400, # 100 GB
        price=14999,
        billing_cycle="year",
        color="#ff9800",
        popular=False,
        has_dashboard=True,
        has_inventory=True,
        has_api_access=True,
        has_analytics=True,
        has_white_label=True,
        has_priority_support=True,
        has_sla_support=True,
        has_custom_reports=True
    )
    
    print("Done! The database plans now match the public pricing page perfectly.")

if __name__ == '__main__':
    seed_plans()
