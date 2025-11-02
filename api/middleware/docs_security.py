"""
Security middleware for API documentation (Swagger/Redoc)
Protects documentation endpoints from public access
"""
from django.http import HttpResponseForbidden, JsonResponse
from django.contrib.auth.models import User
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class DocsSecurityMiddleware:
    """
    Middleware to protect Swagger/Redoc documentation
    Only allows authenticated users or superusers
    """
    
    PROTECTED_PATHS = [
        '/swagger/',
        '/redoc/',
        '/api/docs/',
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Check if path needs protection
        if any(request.path.startswith(path) for path in self.PROTECTED_PATHS):
            # In production, require authentication
            if not settings.DEBUG:
                if not request.user.is_authenticated:
                    return self.access_denied_response(request)
                
                # Optionally require superuser status for docs
                if not request.user.is_superuser:
                    return self.access_denied_response(request)
            # In DEBUG mode, allow access (development only)
        
        return self.get_response(request)
    
    def access_denied_response(self, request):
        """Return access denied response for documentation"""
        if request.path.endswith('.json'):
            return JsonResponse({
                'error': 'Access denied. API documentation requires authentication.',
                'message': 'Please log in to access API documentation.'
            }, status=403)
        else:
            # Return HTML response
            from django.template.loader import render_to_string
            from django.http import HttpResponse
            html = render_to_string('admin/access_denied.html', {
                'site_title': 'Zenith ERP',
                'site_header': 'API Documentation Access Denied'
            })
            return HttpResponse(html, status=403)

