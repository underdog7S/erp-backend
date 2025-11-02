"""
Django management command to update plans to correct values
Run: python manage.py update_plans_final
"""
from django.core.management.base import BaseCommand
from api.models.plan import Plan


class Command(BaseCommand):
    help = 'Update plans to correct pricing and limits matching homepage'

    def handle(self, *args, **options):
        self.stdout.write("Updating Plans to Correct Values...\n")

        # Update Free Plan
        try:
            free = Plan.objects.get(name__iexact='Free')
            free.price = 0
            free.billing_cycle = 'monthly'
            free.max_users = 2
            free.storage_limit_mb = 500
            free.popular = False
            free.has_education = True
            free.has_pharmacy = False
            free.has_retail = False
            free.has_dashboard = True
            free.has_analytics = False
            free.has_api_access = False
            free.save()
            self.stdout.write(self.style.SUCCESS("✅ Free: ₹0/month, 2 users, 500 MB"))
        except Plan.DoesNotExist:
            self.stdout.write(self.style.ERROR("❌ Free plan not found"))

        # Update Starter Plan
        try:
            starter = Plan.objects.get(name__iexact='Starter')
            starter.price = 4500
            starter.billing_cycle = 'annual'
            starter.max_users = 25
            starter.storage_limit_mb = 5120  # 5 GB
            starter.popular = False
            starter.has_education = True
            starter.has_api_access = True
            starter.has_priority_support = True
            starter.has_daily_backups = True
            starter.save()
            self.stdout.write(self.style.SUCCESS("✅ Starter: ₹4,500/year, 25 users, 5 GB"))
        except Plan.DoesNotExist:
            self.stdout.write(self.style.ERROR("❌ Starter plan not found"))

        # Update Pro Plan
        try:
            pro = Plan.objects.get(name__iexact='Pro')
            pro.price = 8999
            pro.billing_cycle = 'annual'
            pro.max_users = 100
            pro.storage_limit_mb = 20480  # 20 GB
            pro.popular = True
            pro.has_education = True
            pro.has_analytics = True
            pro.has_api_access = True
            pro.has_audit_logs = True
            pro.has_priority_support = True
            pro.has_daily_backups = True
            pro.save()
            self.stdout.write(self.style.SUCCESS("✅ Pro: ₹8,999/year, 100 users, 20 GB, POPULAR"))
        except Plan.DoesNotExist:
            self.stdout.write(self.style.ERROR("❌ Pro plan not found"))

        # Update Business Plan
        try:
            business = Plan.objects.get(name__iexact='Business')
            business.price = 19999
            business.billing_cycle = 'annual'
            business.max_users = None  # Unlimited
            business.storage_limit_mb = 51200  # 50 GB
            business.popular = False
            business.has_education = True
            business.has_pharmacy = True
            business.has_retail = True
            business.has_hotel = True
            business.has_restaurant = True
            business.has_salon = True
            business.has_analytics = True
            business.has_api_access = True
            business.has_audit_logs = True
            business.has_priority_support = True
            business.has_daily_backups = True
            business.save()
            self.stdout.write(self.style.SUCCESS("✅ Business: ₹19,999/year, Unlimited users, 50 GB"))
        except Plan.DoesNotExist:
            self.stdout.write(self.style.ERROR("❌ Business plan not found"))

        self.stdout.write(self.style.SUCCESS("\n✅ All plans updated! Refresh admin page to see changes."))

