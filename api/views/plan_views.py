
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from api.models.user import UserProfile, Tenant
from rest_framework import status
from api.models.plan import Plan
from api.models.tenant_features import TenantFeatureConfig
from api.utils.subscription_utils import handle_user_limit_exceeded, reactivate_suspended_users

PLANS = [
    {
        "key": "free",
        "name": "Free",
        "description": "Perfect for small organizations getting started.",
        "max_users": 2,
        "storage_limit_mb": 500,
        "price": 0,
        "billing_cycle": "monthly",
        "features": [
            "1 Industry Module",
            "Basic Dashboard",
            "Up to 2 Users",
            "500 MB Storage",
            "Email Support",
            "Basic Reports",
            "Core ERP Features",
            "Mobile Access"
        ],
        "color": "#4CAF50",
        "popular": False
    },
    {
        "key": "starter",
        "name": "Starter",
        "description": "Great for growing businesses.",
        "max_users": 25,
        "storage_limit_mb": 5120,  # 5 GB
        "price": 4500,
        "billing_cycle": "annual",
        "features": [
            "1 Industry Module",
            "Advanced Dashboard",
            "Up to 25 Users",
            "5 GB Storage",
            "Priority Support",
            "Daily Backups",
            "Advanced Reports",
            "API Access"
        ],
        "color": "#2196F3",
        "popular": False
    },
    {
        "key": "pro",
        "name": "Pro",
        "description": "Perfect for established teams and organizations.",
        "max_users": 100,
        "storage_limit_mb": 20480,  # 20 GB
        "price": 8999,
        "billing_cycle": "annual",
        "features": [
            "1 Industry Module",
            "Advanced Analytics",
            "Up to 100 Users",
            "20 GB Storage",
            "Priority Support",
            "Advanced Analytics",
            "API Access",
            "Custom Integrations",
            "White-label Options",
            "Daily Backups"
        ],
        "color": "#9C27B0",
        "popular": True
    },
    {
        "key": "business_annual",
        "name": "Business",
        "description": "Best value for growing businesses with annual commitment.",
        "max_users": None,  # Unlimited
        "storage_limit_mb": 51200,  # 50 GB
        "price": 19999,
        "billing_cycle": "annual",
        "features": [
            "All Industry Modules",
            "Advanced Analytics & Reports",
            "Unlimited Users",
            "50 GB Storage",
            "24/7 Priority Support",
            "Dedicated Account Manager",
            "Custom Development",
            "SLA Guarantee",
            "On-premise Option",
            "Daily Backups"
        ],
        "annual_bonus": [
            "1-on-1 Strategy Call",
            "Custom Report or Whitepaper",
            "10% Discount on Future Add-Ons",
            "Free Access to New Features for 1 Month"
        ],
        "color": "#FF9800",
        "popular": False,
        "savings": "Save ₹2,989 annually"
    },
    {
        "key": "enterprise",
        "name": "Enterprise",
        "description": "Custom plan for large organizations with unlimited scalability.",
        "max_users": None,  # Unlimited
        "storage_limit_mb": 102400,  # 100 GB
        "price": None,  # Custom
        "billing_cycle": "custom",
        "features": [
            "All Industry Modules",
            "Unlimited Users",
            "100 GB Storage",
            "Advanced Analytics & Reports",
            "SLA Support",
            "Phone/Chat Support",
            "White-label Solution",
            "Custom Onboarding",
            "Dedicated Account Manager",
            "Custom Integrations",
            "Priority Support"
        ],
        "color": "#F44336",
        "popular": False
    },
]

class PlanListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(PLANS)

class PlanChangeView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        profile = UserProfile.objects.get(user=request.user)
        if not profile.role or profile.role.name != "admin":
            return Response({"error": "Only admins can change the plan."}, status=status.HTTP_403_FORBIDDEN)
        tenant = profile.tenant
        plan_key = request.data.get("plan")
        plan_obj = next((p for p in PLANS if p["key"] == plan_key), None)
        if not plan_obj:
            return Response({"error": "Invalid plan selected."}, status=status.HTTP_400_BAD_REQUEST)
        # Update the tenant's plan (must assign a Plan object)
        try:
            plan_instance = Plan.objects.get(name__iexact=plan_obj["name"])
            old_plan = tenant.plan
            old_price = old_plan.price if old_plan and old_plan.price is not None else 0
            new_price = plan_instance.price

            # This endpoint performs no payment verification, so it must never
            # move a tenant to a costlier plan - only sideways/downgrades (e.g.
            # switching to Free) are safe to self-serve here. Paid upgrades must
            # go through the Razorpay order/verify flow, which activates the
            # plan itself once a matching payment is confirmed.
            if new_price is None:
                return Response({"error": "This plan requires contacting sales."}, status=status.HTTP_400_BAD_REQUEST)
            if new_price > old_price:
                return Response({"error": "Upgrading to a paid plan requires completing payment first."}, status=status.HTTP_402_PAYMENT_REQUIRED)

            tenant.plan = plan_instance
            tenant.save()
            
            # Check if downgrading (new plan has fewer users)
            if old_plan and old_plan.max_users and plan_instance.max_users:
                if plan_instance.max_users < old_plan.max_users:
                    # Handle user limit exceeded
                    result = handle_user_limit_exceeded(tenant)
                    return Response({
                        "message": f"Plan changed to {plan_instance.name}.",
                        "plan": plan_instance.name,
                        "warning": result['message'],
                        "suspended_count": result['suspended_count']
                    })
            
            # If upgrading, reactivate any suspended users
            if old_plan and plan_instance.max_users:
                if not old_plan.max_users or (plan_instance.max_users > old_plan.max_users):
                    result = reactivate_suspended_users(tenant)
                    if result['reactivated_count'] > 0:
                        return Response({
                            "message": f"Plan changed to {plan_instance.name}.",
                            "plan": plan_instance.name,
                            "reactivated_users": result['reactivated_count']
                        })
            
            return Response({"message": f"Plan changed to {plan_instance.name}.", "plan": plan_instance.name})
        except Plan.DoesNotExist:
            return Response({"error": "Plan object not found in DB."}, status=status.HTTP_400_BAD_REQUEST)

class TenantFeatureUsageView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = UserProfile.objects.get(user=request.user)
        tenant = profile.tenant
        
        # Get or create feature config
        config, created = TenantFeatureConfig.objects.get_or_create(tenant=tenant)
        
        return Response({
            "email": {
                "enabled": config.is_custom_email_enabled,
                "domain": config.custom_domain
            },
            "sms": {
                "enabled": config.is_sms_enabled,
                "used": config.sms_used_this_month,
                "limit": config.sms_monthly_limit
            },
            "whatsapp": {
                "enabled": config.is_whatsapp_enabled,
                "used": config.whatsapp_used_this_month,
                "limit": config.whatsapp_monthly_limit
            },
            "ai": {
                "enabled": config.is_ai_enabled,
                "used": config.ai_tokens_used_this_month,
                "limit": config.ai_tokens_monthly_limit
            }
        })
