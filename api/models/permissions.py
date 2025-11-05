from rest_framework.permissions import BasePermission
from api.models.user import UserProfile
from rest_framework.response import Response


class IsTenantMember(BasePermission):
    """
    Permission check to ensure user belongs to a tenant
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        try:
            profile = UserProfile.objects.get(user=request.user)
            return profile.tenant is not None
        except UserProfile.DoesNotExist:
            return False


def HasFeaturePermissionFactory(feature_name):
    """
    Factory function to create permission class that checks if user's plan has a specific feature.
    Returns proper error messages when feature is not available.
    """
    class _HasFeaturePermission(BasePermission):
        def has_permission(self, request, view):
            if not request.user or not request.user.is_authenticated:
                return False
            try:
                profile = UserProfile._default_manager.get(user=request.user)
                tenant = profile.tenant
                
                if not tenant:
                    return False
                
                plan = tenant.plan
                if not plan:
                    # No plan assigned
                    return False
                
                # Check if plan has the feature
                has_feature = plan.has_feature(feature_name)
                
                if not has_feature:
                    # Feature not available - return detailed error message
                    from rest_framework.exceptions import PermissionDenied
                    feature_display_name = feature_name.replace('_', ' ').title()
                    
                    # Get plan name and suggest upgrade
                    current_plan = plan.name
                    error_message = (
                        f"{feature_display_name} module is not available in your current plan ({current_plan}). "
                        f"Please upgrade to a plan that includes {feature_display_name} to access this feature."
                    )
                    
                    # Raise PermissionDenied with detailed message
                    raise PermissionDenied(detail=error_message)
                
                return True
            except PermissionDenied:
                # Re-raise PermissionDenied exceptions
                raise
            except Exception:
                # For other exceptions, return False (will show generic 403)
                return False
        
        def get_error_message(self, request, view):
            """Get error message for when permission is denied"""
            try:
                profile = UserProfile._default_manager.get(user=request.user)
                tenant = profile.tenant
                plan = tenant.plan if tenant else None
                
                feature_display_name = feature_name.replace('_', ' ').title()
                current_plan = plan.name if plan else "No Plan"
                
                return (
                    f"{feature_display_name} module is not available in your current plan ({current_plan}). "
                    f"Please upgrade to a plan that includes {feature_display_name} to access this feature."
                )
            except:
                return f"{feature_name.replace('_', ' ').title()} feature is not available. Please upgrade your plan."
    
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


class IsPaidUser(BasePermission):
    """
    Permission class to check if user has a paid plan.
    A paid user is someone who has:
    1. A plan with price > 0 (paid plan)
    2. OR a plan with custom pricing (price is None)
    3. Free plan users (price = 0) are excluded
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        try:
            profile = UserProfile._default_manager.get(user=request.user)
            tenant = profile.tenant
            
            if not tenant:
                return False
            
            # Check if tenant has a paid plan
            plan = tenant.plan
            if not plan:
                return False
            
            # Check if plan is paid
            # Custom pricing (price is None) is considered paid
            # Free plan (price = 0) is not allowed
            if plan.price is None:
                # Custom pricing - considered paid
                return True
            
            if plan.price is not None and plan.price > 0:
                # Paid plan
                return True
            
            # Free plan (price = 0) - not allowed
            return False
            
        except UserProfile.DoesNotExist:
            return False
        except Exception:
            return False 