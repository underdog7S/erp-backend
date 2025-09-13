
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from api.models.user import UserProfile, Tenant
from rest_framework import status
from api.models.plan import Plan

PLANS = [
    {
        "key": "free",
        "name": "Free",
        "description": "Perfect for small organizations getting started.",
        "max_users": 5,
        "storage_limit_mb": 500,
        "price": 0,
        "billing_cycle": "monthly",
        "features": [
            "1 Industry Module",
            "Basic Dashboard",
            "Up to 5 Users",
            "500 MB Storage",
            "Email Support",
            "Basic Reports"
        ],
        "color": "#4CAF50",
        "popular": False
    },
    {
        "key": "starter",
        "name": "Starter",
        "description": "Great for growing businesses.",
        "max_users": 20,
        "storage_limit_mb": 2048,  # 2 GB
        "price": 999,
        "billing_cycle": "annual",
        "features": [
            "1 Industry Module",
            "Advanced Dashboard",
            "Up to 20 Users",
            "2 GB Storage",
            "Email Support",
            "Daily Backups",
            "Enhanced Reports"
        ],
        "color": "#2196F3",
        "popular": False
    },
    {
        "key": "pro",
        "name": "Pro",
        "description": "Perfect for established teams and organizations.",
        "max_users": 50,
        "storage_limit_mb": 10240,  # 10 GB
        "price": 2499,
        "billing_cycle": "annual",
        "features": [
            "1 Industry Module",
            "Advanced Analytics",
            "Up to 50 Users",
            "10 GB Storage",
            "Priority Email Support",
            "Audit Logs",
            "API Access",
            "Quality Control",
            "Billing Management",
            "Daily Backups"
        ],
        "color": "#9C27B0",
        "popular": True
    },
    {
        "key": "business_annual",
        "name": "Business",
        "description": "Best value for growing businesses with annual commitment.",
        "max_users": 150,
        "storage_limit_mb": 20480,  # 20 GB
        "price": 4999,
        "billing_cycle": "annual",
        "features": [
            "1 Industry Module",
            "Advanced Analytics & Reports",
            "Up to 150 Users",
            "20 GB Storage",
            "Email + Chat Support",
            "Priority Onboarding",
            "Audit Logs",
            "API Access",
            "Quality Control",
            "Billing Management",
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
            tenant.plan = plan_instance
            tenant.save()
            return Response({"message": f"Plan changed to {plan_instance.name}.", "plan": plan_instance.name})
        except Plan.DoesNotExist:
            return Response({"error": "Plan object not found in DB."}, status=status.HTTP_400_BAD_REQUEST)
