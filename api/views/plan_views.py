from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from api.models.user import UserProfile, Tenant
from rest_framework import status
from api.models.plan import Plan
from api.models.tenant_features import TenantFeatureConfig

def serialize_plan(p):
    """Serialize a Plan model instance into the dictionary expected by the frontend"""
    # Map boolean features to a list of strings
    features = []
    if p.has_api_access: features.append("API Access")
    if p.has_dashboard: features.append("Advanced Dashboard")
    if p.has_analytics: features.append("Advanced Analytics")
    if p.has_priority_support: features.append("Priority Support")
    if p.has_daily_backups: features.append("Daily Backups")
    if p.has_white_label: features.append("White-Label Ready")
    if p.has_custom_reports: features.append("Custom Reports")

    if p.name.lower() == 'platform':
        features.append("Plug In Your Own WhatsApp")
        features.append("Plug In Your Own SMS Gateway")
        features.append("Plug In Your Own Email (SMTP)")
        features.append("Full ERP Platform Access")
    elif p.name.lower() == 'starter':
        features.append("Dedicated SMS Number (We Set Up)")
        features.append("Dedicated WhatsApp Number (We Set Up)")
        features.append("Dedicated Support Email (We Set Up)")
    elif p.name.lower() == 'pro':
        features.append("Dedicated SMS/WhatsApp Number (We Set Up)")
        features.append("Dedicated Support Email (We Set Up)")
        features.append("Priority White-Glove Onboarding")
    elif p.name.lower() == 'enterprise':
        features.append("Bring Your Own Key (Full BYOK)")
        features.append("Unlimited Users")
        features.append("White-Label Branding")
    
    return {
        "key": p.name.lower(),
        "name": p.name,
        "description": p.description,
        "max_users": p.max_users,
        "storage_limit_mb": p.storage_limit_mb,
        "price": float(p.price),
        "billing_cycle": p.billing_cycle,
        "color": p.color,
        "popular": p.popular,
        "features": features
    }

class PlanListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        plans = Plan.objects.order_by('price')
        data = [serialize_plan(p) for p in plans]
        return Response(data)

class PlanChangeView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        profile = UserProfile.objects.get(user=request.user)
        if not profile.role or profile.role.name != "admin":
            return Response({"error": "Only admins can change the plan."}, status=status.HTTP_403_FORBIDDEN)
        
        tenant = profile.tenant
        plan_key = request.data.get("plan")

        # Look up by name lowercased
        try:
            plan_instance = Plan.objects.get(name__iexact=plan_key)
        except Plan.DoesNotExist:
            return Response({"error": "Invalid plan selected."}, status=status.HTTP_400_BAD_REQUEST)

        old_plan = tenant.plan
        old_price = old_plan.price if old_plan and old_plan.price is not None else 0
        new_price = plan_instance.price

        # SECURITY: this endpoint is not payment-verified. It may only ever
        # move a tenant DOWN to a cheaper/free plan for self-service
        # downgrades. Any upgrade to a plan that costs more must go through
        # RazorpayPaymentVerifyView, which actually confirms payment with
        # Razorpay before calling provision_tenant_plan_features(). Without
        # this check, anyone could POST {"plan":"enterprise"} here and get
        # a paid tier for free.
        if new_price is None or new_price > old_price:
            return Response(
                {"error": "Upgrading to a paid plan requires completing checkout. Please use the billing/upgrade flow instead."},
                status=status.HTTP_403_FORBIDDEN
            )

        tenant.plan = plan_instance
        tenant.save()

        from api.utils.subscription_utils import provision_tenant_plan_features
        provision_tenant_plan_features(tenant, plan_instance)

        return Response({"message": f"Successfully changed plan to {plan_instance.name}."})

class TenantFeatureUsageView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = UserProfile.objects.get(user=request.user)
            tenant = profile.tenant
            if not tenant:
                return Response({'error': 'Tenant not found'}, status=status.HTTP_404_NOT_FOUND)
                
            config, _ = TenantFeatureConfig.objects.get_or_create(tenant=tenant)
            
            return Response({
                'plan': tenant.plan.name if tenant.plan else 'free',
                'sms': {
                    'enabled': config.is_sms_enabled,
                    'used': config.sms_used_this_month,
                    'limit': config.sms_monthly_limit
                },
                'whatsapp': {
                    'enabled': config.is_whatsapp_enabled,
                    'used': config.whatsapp_used_this_month,
                    'limit': config.whatsapp_monthly_limit
                },
                'ai': {
                    'enabled': config.is_ai_enabled,
                    'used': config.ai_tokens_used_this_month,
                    'limit': config.ai_tokens_monthly_limit
                },
                'managed_assets': {
                    'phone_number': config.managed_phone_number,
                    'email_address': config.managed_email_address
                }
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
