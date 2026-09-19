from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from api.models.user import UserProfile, Tenant
from rest_framework import status
from api.models.plan import Plan
from api.models.tenant_features import TenantFeatureConfig
from api.utils.subscription_utils import handle_user_limit_exceeded, reactivate_suspended_users

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

        if new_price > old_price and plan_instance.name.lower() != "free":
             pass

        tenant.plan = plan_instance
        tenant.save()

        # Create missing config if needed
        config, _ = TenantFeatureConfig.objects.get_or_create(tenant=tenant)
        
        # Auto-provision APIs based on the new plan
        plan_name = plan_instance.name.lower()
        if plan_name == 'starter':
            config.is_sms_enabled = True
            config.sms_monthly_limit = 1000
            config.is_whatsapp_enabled = False
            config.is_ai_enabled = True
            config.ai_tokens_monthly_limit = 500
        elif plan_name == 'pro':
            config.is_sms_enabled = True
            config.sms_monthly_limit = 5000
            config.is_whatsapp_enabled = True
            config.whatsapp_monthly_limit = 1000
            config.is_ai_enabled = True
            config.ai_tokens_monthly_limit = 2000
        elif plan_name == 'enterprise':
            config.is_sms_enabled = True
            config.sms_monthly_limit = 20000
            config.is_whatsapp_enabled = True
            config.whatsapp_monthly_limit = 10000
            config.is_ai_enabled = True
            config.ai_tokens_monthly_limit = 10000
        elif plan_name == 'free':
            config.is_sms_enabled = False
            config.is_whatsapp_enabled = False
            config.is_ai_enabled = False
            
        config.save()

        # Trigger logic based on new plan constraints
        if tenant.plan.max_users is not None:
            active_users = UserProfile.objects.filter(tenant=tenant, is_active=True).count()
            if active_users > tenant.plan.max_users:
                handle_user_limit_exceeded(tenant)
            else:
                reactivate_suspended_users(tenant)

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
                }
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
