"""
Security utility functions for endpoint protection
"""
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from django.conf import settings


def access_denied_response(request, message="Access denied", status_code=403):
    """
    Return standardized access denied response
    """
    if request.path.endswith('.json') or 'application/json' in request.META.get('HTTP_ACCEPT', ''):
        return JsonResponse({
            'error': 'Access denied',
            'message': message,
            'status_code': status_code
        }, status=status_code)
    else:
        html = render_to_string('admin/access_denied.html', {
            'site_title': 'Zenith ERP',
            'site_header': message
        })
        return HttpResponse(html, status=status_code)


def is_public_endpoint(path):
    """
    Check if an endpoint should be publicly accessible
    """
    public_paths = [
        '/api/login/',
        '/api/register/',
        '/api/token/refresh/',
        '/api/verify-email/',
        '/api/resend-verification/',
        '/api/auth/google/',
        '/api/auth/google/callback/',
        '/api/plans/',
        '/api/public/',  # Public widget endpoints
    ]
    
    return any(path.startswith(p) for p in public_paths)


def should_require_auth(path):
    """
    Determine if a path should require authentication
    """
    # Public endpoints
    if is_public_endpoint(path):
        return False
    
    # Documentation endpoints - require auth in production
    docs_paths = ['/swagger/', '/redoc/', '/api-docs/']
    if any(path.startswith(p) for p in docs_paths):
        return not settings.DEBUG  # Require auth unless DEBUG mode
    
    # Admin endpoints - always require superuser
    admin_paths = ['/admin/', '/secure-admin/']
    if any(path.startswith(p) for p in admin_paths):
        return True
    
    # Default: require authentication
    return True

