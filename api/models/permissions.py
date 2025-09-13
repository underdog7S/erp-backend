from rest_framework.permissions import BasePermission
from api.models.user import UserProfile
from rest_framework.response import Response

def HasFeaturePermissionFactory(feature_name):
    class _HasFeaturePermission(BasePermission):
        def has_permission(self, request, view):
            if not request.user or not request.user.is_authenticated:
                return False
            try:
                profile = UserProfile._default_manager.get(user=request.user)
                tenant = profile.tenant
                plan = tenant.plan
                if not plan:
                    return False
                return plan.has_feature(feature_name)
            except Exception:
                return False
    _HasFeaturePermission.__name__ = f"Has{feature_name.capitalize()}FeaturePermission"
    return _HasFeaturePermission

def role_required(*roles):
    def decorator(view_func):
        def _wrapped_view(self, request, *args, **kwargs):
            profile = UserProfile._default_manager.get(user=request.user)
            if profile.role and profile.role.name in roles:
                return view_func(self, request, *args, **kwargs)
            return Response({'error': 'Permission denied.'}, status=403)
        return _wrapped_view
    return decorator

def role_exclude(*excluded_roles):
    def decorator(view_func):
        def _wrapped_view(self, request, *args, **kwargs):
            profile = UserProfile._default_manager.get(user=request.user)
            if profile.role and profile.role.name not in excluded_roles:
                return view_func(self, request, *args, **kwargs)
            return Response({'error': 'Permission denied.'}, status=403)
        return _wrapped_view
    return decorator 