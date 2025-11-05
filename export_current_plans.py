#!/usr/bin/env python
"""
Export current plan configurations to a readable format
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
# Try to auto-detect settings module
if os.path.exists('zenith_erp'):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zenith_erp.settings')
elif os.path.exists('config'):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
else:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from api.models.plan import Plan

def export_plans():
    plans = Plan.objects.all().order_by('price' if Plan.price else 'id')
    
    print("=" * 80)
    print("CURRENT PLAN CONFIGURATIONS")
    print("=" * 80)
    print()
    
    for i, plan in enumerate(plans, 1):
        print(f"PLAN {i}: {plan.name.upper()}")
        print("-" * 80)
        
        # Basic Information
        print(f"Name: {plan.name}")
        print(f"Description: {plan.description or '(No description)'}")
        print(f"Popular: {'Yes ✓' if plan.popular else 'No'}")
        print(f"Color: {plan.color}")
        print(f"Savings Text: {plan.savings_text or '(None)'}")
        print()
        
        # Pricing
        print("PRICING:")
        if plan.price is None:
            print(f"  Price: Custom Pricing")
            print(f"  Billing Cycle: {plan.billing_cycle}")
        elif plan.price == 0:
            print(f"  Price: ₹0 (Free)")
            print(f"  Billing Cycle: {plan.billing_cycle}")
        else:
            print(f"  Price: ₹{plan.price:,.2f}")
            print(f"  Billing Cycle: {plan.billing_cycle}")
            if plan.monthly_equivalent:
                print(f"  Monthly Equivalent: ₹{plan.monthly_equivalent:,.2f}/month")
        print()
        
        # Limits
        print("LIMITS:")
        if plan.max_users is None:
            print(f"  Max Users: Unlimited")
        else:
            print(f"  Max Users: {plan.max_users} users")
        gb = plan.storage_limit_mb / 1024
        if gb >= 1:
            print(f"  Storage: {gb:.1f} GB ({plan.storage_limit_mb:,} MB)")
        else:
            print(f"  Storage: {plan.storage_limit_mb} MB")
        print()
        
        # Modules
        modules = []
        if plan.has_education: modules.append("Education")
        if plan.has_pharmacy: modules.append("Pharmacy")
        if plan.has_retail: modules.append("Retail")
        if plan.has_hotel: modules.append("Hotel")
        if plan.has_restaurant: modules.append("Restaurant")
        if plan.has_salon: modules.append("Salon")
        if plan.has_healthcare: modules.append("Healthcare")
        
        print(f"MODULES ({len(modules)} enabled):")
        if modules:
            for module in modules:
                print(f"  ✓ {module}")
        else:
            print("  (No modules enabled)")
        print()
        
        # Core Features
        features = []
        if plan.has_dashboard: features.append("Dashboard")
        if plan.has_analytics: features.append("Analytics")
        if plan.has_api_access: features.append("API Access")
        if plan.has_audit_logs: features.append("Audit Logs")
        if plan.has_priority_support: features.append("Priority Support")
        if plan.has_phone_support: features.append("Phone Support")
        if plan.has_white_label: features.append("White Label")
        if plan.has_onboarding: features.append("Onboarding")
        if plan.has_sla_support: features.append("SLA Support")
        if plan.has_daily_backups: features.append("Daily Backups")
        if plan.has_custom_reports: features.append("Custom Reports")
        if plan.has_billing: features.append("Billing")
        if plan.has_qc: features.append("Quality Control")
        if plan.has_inventory: features.append("Inventory")
        
        print(f"CORE FEATURES ({len(features)} enabled):")
        if features:
            for feature in features:
                print(f"  ✓ {feature}")
        else:
            print("  (No core features enabled)")
        print()
        
        # Premium Features
        premium = []
        if plan.has_strategy_call: premium.append("Strategy Call")
        if plan.has_future_discount: premium.append("Future Discount")
        if plan.has_new_features_access: premium.append("New Features Access")
        
        if premium:
            print(f"PREMIUM FEATURES ({len(premium)} enabled):")
            for feature in premium:
                print(f"  ✓ {feature}")
            print()
        
        print("=" * 80)
        print()

if __name__ == '__main__':
    export_plans()


