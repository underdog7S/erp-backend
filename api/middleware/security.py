"""
Security middleware for rate limiting and request validation
"""
from django.core.cache import cache
from django.http import JsonResponse
from django.utils import timezone
import json
import logging

logger = logging.getLogger(__name__)

class RateLimitMiddleware:
    """
    Rate limiting middleware to prevent API abuse
    More lenient for authenticated users
    """
    def __init__(self, get_response):
        self.get_response = get_response
        # Rate limits per IP - unauthenticated users
        self.rate_limit_per_minute_unauth = 60  # 60 requests per minute
        self.rate_limit_per_hour_unauth = 1000  # 1000 requests per hour
        
        # Rate limits per IP - authenticated users (more lenient)
        self.rate_limit_per_minute_auth = 300  # 300 requests per minute (increased for dashboard loads)
        self.rate_limit_per_hour_auth = 10000  # 10000 requests per hour (increased)
        
        self.rate_limit_per_day = 10000  # 10000 requests per day (same for both)

    def __call__(self, request):
        # Skip rate limiting for static/media files
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return self.get_response(request)

        # Skip rate limiting for admin panel (different protection)
        if request.path.startswith('/admin/') or request.path.startswith('/secure-admin/'):
            return self.get_response(request)
        
        # Skip rate limiting for notification polling endpoints (high-frequency but necessary)
        if '/api/notifications' in request.path:
            return self.get_response(request)

        # Check if user is authenticated (safely - request.user might not exist yet)
        is_authenticated = False
        if hasattr(request, 'user') and request.user:
            try:
                is_authenticated = request.user.is_authenticated
            except AttributeError:
                # request.user exists but doesn't have is_authenticated (shouldn't happen, but be safe)
                is_authenticated = False
        
        # Use different limits based on authentication
        if is_authenticated:
            minute_limit = self.rate_limit_per_minute_auth
            hour_limit = self.rate_limit_per_hour_auth
        else:
            minute_limit = self.rate_limit_per_minute_unauth
            hour_limit = self.rate_limit_per_hour_unauth

        # Get client IP (use user ID for authenticated users if available)
        if is_authenticated and hasattr(request, 'user') and request.user and hasattr(request.user, 'id'):
            # For authenticated users, use user ID + IP for better tracking
            try:
                identifier = f"user_{request.user.id}_{self.get_client_ip(request)}"
            except (AttributeError, TypeError):
                # Fallback to IP only if user.id access fails
                identifier = self.get_client_ip(request)
        else:
            identifier = self.get_client_ip(request)
        
        # Check per-minute limit
        if not self.check_rate_limit(identifier, 'minute', minute_limit, 60):
            logger.warning(f"Rate limit exceeded (minute) for {'user' if is_authenticated else 'IP'}: {identifier}")
            return JsonResponse(
                {
                    'error': 'Rate limit exceeded. Please try again later.',
                    'retry_after': 60
                },
                status=429
            )
        
        # Check per-hour limit
        if not self.check_rate_limit(identifier, 'hour', hour_limit, 3600):
            logger.warning(f"Rate limit exceeded (hour) for {'user' if is_authenticated else 'IP'}: {identifier}")
            return JsonResponse(
                {
                    'error': 'Hourly rate limit exceeded. Please try again later.',
                    'retry_after': 3600
                },
                status=429
            )
        
        # Check per-day limit (same for both)
        if not self.check_rate_limit(identifier, 'day', self.rate_limit_per_day, 86400):
            logger.warning(f"Rate limit exceeded (day) for {'user' if is_authenticated else 'IP'}: {identifier}")
            return JsonResponse(
                {
                    'error': 'Daily rate limit exceeded. Please contact support.',
                    'retry_after': 86400
                },
                status=429
            )
        
        return self.get_response(request)
    
    def check_rate_limit(self, ip, period, limit, timeout):
        """Check if IP has exceeded rate limit for given period"""
        key = f"ratelimit_{period}_{ip}"
        count = cache.get(key, 0)
        
        if count >= limit:
            return False
        
        cache.set(key, count + 1, timeout)
        return True
    
    def get_client_ip(self, request):
        """Extract client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class SecurityHeadersMiddleware:
    """
    Add security headers to all responses
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # HTTPS-only in production
        if not request.get_host().startswith('localhost') and not request.get_host().startswith('127.0.0.1'):
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        return response


class RequestValidationMiddleware:
    """
    Validate and sanitize incoming requests
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.max_request_size = 10 * 1024 * 1024  # 10MB

    def __call__(self, request):
        # Check request size
        if hasattr(request, 'META') and 'CONTENT_LENGTH' in request.META:
            try:
                content_length = int(request.META['CONTENT_LENGTH'])
                if content_length > self.max_request_size:
                    return JsonResponse(
                        {'error': 'Request too large. Maximum size is 10MB.'},
                        status=413
                    )
            except (ValueError, TypeError):
                pass
        
        # Validate request method
        allowed_methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD']
        if request.method not in allowed_methods:
            return JsonResponse(
                {'error': f'Method {request.method} not allowed'},
                status=405
            )
        
        return self.get_response(request)

