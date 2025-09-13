from django.core.management.base import BaseCommand
from api.models.plan import Plan

class Command(BaseCommand):
    help = 'Setup all plans in the database'

    def handle(self, *args, **options):
        plans_data = [
            {
                'name': 'Free',
                'description': 'Perfect for small organizations getting started.',
                'max_users': 5,
                'storage_limit_mb': 500,
                'price': 0,
                'billing_cycle': 'monthly',
                'color': '#4CAF50',
                'popular': False,
                'has_dashboard': True,
                'has_inventory': False,
                'has_education': True,
                'has_pharmacy': True,
                'has_retail': True,
                'has_healthcare': False,
                'has_hotel': True,
                'has_restaurant': True,
                'has_salon': True,
                'has_analytics': False,
                'has_qc': False,
                'has_billing': False,
                'has_api_access': False,
                'has_audit_logs': False,
                'has_priority_support': False,
                'has_phone_support': False,
                'has_white_label': False,
                'has_onboarding': False,
                'has_sla_support': False,
                'has_daily_backups': False,
                'has_strategy_call': False,
                'has_custom_reports': False,
                'has_future_discount': False,
                'has_new_features_access': False,
            },
            {
                'name': 'Starter',
                'description': 'Great for growing businesses.',
                'max_users': 20,
                'storage_limit_mb': 2048,  # 2 GB
                'price': 999,
                'billing_cycle': 'annual',
                'color': '#2196F3',
                'popular': False,
                'has_dashboard': True,
                'has_inventory': True,
                'has_education': True,
                'has_pharmacy': True,
                'has_retail': True,
                'has_healthcare': True,
                'has_hotel': True,
                'has_restaurant': True,
                'has_salon': True,
                'has_analytics': False,
                'has_qc': False,
                'has_billing': False,
                'has_api_access': False,
                'has_audit_logs': False,
                'has_priority_support': False,
                'has_phone_support': False,
                'has_white_label': False,
                'has_onboarding': False,
                'has_sla_support': False,
                'has_daily_backups': True,
                'has_strategy_call': False,
                'has_custom_reports': False,
                'has_future_discount': False,
                'has_new_features_access': False,
            },
            {
                'name': 'Pro',
                'description': 'Perfect for established teams and organizations.',
                'max_users': 50,
                'storage_limit_mb': 10240,  # 10 GB
                'price': 2499,
                'billing_cycle': 'annual',
                'color': '#9C27B0',
                'popular': True,
                'has_dashboard': True,
                'has_inventory': True,
                'has_education': True,
                'has_pharmacy': True,
                'has_retail': True,
                'has_healthcare': True,
                'has_hotel': True,
                'has_restaurant': True,
                'has_salon': True,
                'has_analytics': True,
                'has_qc': True,
                'has_billing': True,
                'has_api_access': True,
                'has_audit_logs': True,
                'has_priority_support': True,
                'has_phone_support': False,
                'has_white_label': False,
                'has_onboarding': False,
                'has_sla_support': False,
                'has_daily_backups': True,
                'has_strategy_call': False,
                'has_custom_reports': False,
                'has_future_discount': False,
                'has_new_features_access': False,
            },
            {
                'name': 'Business',
                'description': 'Best value for growing businesses with annual commitment.',
                'max_users': 150,
                'storage_limit_mb': 20480,  # 20 GB
                'price': 4999,
                'billing_cycle': 'annual',
                'color': '#FF9800',
                'popular': False,
                'has_dashboard': True,
                'has_inventory': True,
                'has_education': True,
                'has_pharmacy': True,
                'has_retail': True,
                'has_healthcare': True,
                'has_hotel': True,
                'has_restaurant': True,
                'has_salon': True,
                'has_analytics': True,
                'has_qc': True,
                'has_billing': True,
                'has_api_access': True,
                'has_audit_logs': True,
                'has_priority_support': True,
                'has_phone_support': False,
                'has_white_label': False,
                'has_onboarding': True,
                'has_sla_support': False,
                'has_daily_backups': True,
                'has_strategy_call': True,
                'has_custom_reports': True,
                'has_future_discount': True,
                'has_new_features_access': True,
            },
            {
                'name': 'Enterprise',
                'description': 'Custom plan for large organizations with unlimited scalability.',
                'max_users': None,  # Unlimited
                'storage_limit_mb': 102400,  # 100 GB
                'price': None,  # Custom
                'billing_cycle': 'custom',
                'color': '#F44336',
                'popular': False,
                'has_dashboard': True,
                'has_inventory': True,
                'has_education': True,
                'has_pharmacy': True,
                'has_retail': True,
                'has_healthcare': True,
                'has_hotel': True,
                'has_restaurant': True,
                'has_salon': True,
                'has_analytics': True,
                'has_qc': True,
                'has_billing': True,
                'has_api_access': True,
                'has_audit_logs': True,
                'has_priority_support': True,
                'has_phone_support': True,
                'has_white_label': True,
                'has_onboarding': True,
                'has_sla_support': True,
                'has_daily_backups': True,
                'has_strategy_call': True,
                'has_custom_reports': True,
                'has_future_discount': True,
                'has_new_features_access': True,
            },
        ]

        for plan_data in plans_data:
            plan, created = Plan.objects.get_or_create(
                name=plan_data['name'],
                defaults=plan_data
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully created plan "{plan.name}"')
                )
            else:
                # Update existing plan with new data
                for key, value in plan_data.items():
                    setattr(plan, key, value)
                plan.save()
                self.stdout.write(
                    self.style.WARNING(f'Updated existing plan "{plan.name}"')
                )

        self.stdout.write(
            self.style.SUCCESS('Successfully setup all plans!')
        ) 