"""
Subscription Middleware
Checks subscription status for API requests and enforces restrictions
"""
from django.utils import timezone
from rest_framework.response import Response
from rest_framework import status
from api.models.user import UserProfile

class SubscriptionMiddleware:
    """
    Middleware to check subscription status and enforce restrictions
    This protects all API endpoints except authentication and public endpoints
    """
    
    # Endpoints that don't require subscription check
    EXEMPT_PATHS = [
        '/api/login/',
        '/api/register/',
        '/api/token/refresh/',
        '/api/plans/',
        '/api/payments/create-order/',
        '/api/payments/verify/',
        '/api/auth/google/',
        '/api/auth/google/callback/',
        '/api/verify-email/',
        '/api/resend-verification/',
    ]
    
    # Read-only methods (allowed in grace period)
    READ_ONLY_METHODS = ['GET', 'HEAD', 'OPTIONS']
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Check if path should be exempt
        if any(request.path.startswith(exempt) for exempt in self.EXEMPT_PATHS):
            return self.get_response(request)
        
        # Only check authenticated requests
        if not request.user.is_authenticated:
            return self.get_response(request)
        
        try:
            profile = UserProfile.objects.get(user=request.user)
            tenant = profile.tenant
            
            # Check if subscription has expired
            if tenant.is_subscription_expired():
                if tenant.subscription_status == 'expired':
                    # Block all access
                    return Response({
                        'error': 'Your plan has expired. Please renew to continue using the service.',
                        'subscription_end_date': tenant.subscription_end_date.isoformat() if tenant.subscription_end_date else None,
                        'action_url': '/admin/plans',
                        'renewal_required': True
                    }, status=status.HTTP_403_FORBIDDEN)
                elif tenant.is_in_grace_period():
                    # Allow read-only access in grace period
                    if request.method not in self.READ_ONLY_METHODS:
                        return Response({
                            'error': 'Your plan has expired. You are in a grace period with read-only access. Please renew to restore full functionality.',
                            'subscription_end_date': tenant.subscription_end_date.isoformat() if tenant.subscription_end_date else None,
                            'grace_period_end': tenant.grace_period_end_date.isoformat() if tenant.grace_period_end_date else None,
                            'action_url': '/admin/plans',
                            'renewal_required': True
                        }, status=status.HTTP_403_FORBIDDEN)
            
            return self.get_response(request)
        except UserProfile.DoesNotExist:
            # If no profile, allow request to proceed (might be first-time login)
            return self.get_response(request)
        except Exception as e:
            # Log error but don't block request
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Subscription middleware error: {e}")
            return self.get_response(request)

