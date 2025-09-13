from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from api.models.user import UserProfile
from api.models.permissions import role_required

class DashboardView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = UserProfile._default_manager.get(user=request.user)
        tenant = profile.tenant
        plan = tenant.plan
        # Calculate storage used (sum all user profile photo sizes for this tenant)
        total_bytes = 0
        profiles = UserProfile._default_manager.filter(tenant=tenant).exclude(photo='').exclude(photo=None)
        for p in profiles:
            if p.photo and hasattr(p.photo, 'size'):
                total_bytes += p.photo.size
        storage_used_mb = round(total_bytes / (1024 * 1024), 2)
        plan_limits = {
            "max_users": plan.max_users if plan else None,
            "storage_limit_mb": plan.storage_limit_mb if plan else None,
        }
        # Example: return some dashboard stats
        data = {
            'tenant': tenant.name,
            'industry': tenant.industry,
            'plan': plan.name if plan else None,
            'storage_used_mb': storage_used_mb,
            'storage_limit_mb': plan.storage_limit_mb if plan else None,
            'plan_limits': plan_limits,
            'user_count': UserProfile.objects.filter(tenant=tenant).count(),
        }
        return Response(data)

class AlertsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Return empty alerts for now
        return Response([])

class StorageUsageView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = UserProfile.objects.get(user=request.user)
        tenant = profile.tenant
        return Response({
            'storage_used_mb': tenant.storage_used_mb,
            'storage_limit_mb': tenant.plan.storage_limit_mb if tenant.plan else None,
        }) 