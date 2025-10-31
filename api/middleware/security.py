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
    """
    def __init__(self, get_response):
        self.get_response = get_response
        # Rate limits per IP
        self.rate_limit_per_minute = 60  # 60 requests per minute
        self.rate_limit_per_hour = 1000  # 1000 requests per hour
        self.rate_limit_per_day = 10000  # 10000 requests per day

    def __call__(self, request):
        # Skip rate limiting for static/media files
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return self.get_response(request)

        # Skip rate limiting for admin panel (different protection)
        if request.path.startswith('/admin/'):
            return self.get_response(request)

        # Get client IP
        ip = self.get_client_ip(request)
        
        # Check per-minute limit
        if not self.check_rate_limit(ip, 'minute', self.rate_limit_per_minute, 60):
            logger.warning(f"Rate limit exceeded (minute) for IP: {ip}")
            return JsonResponse(
                {
                    'error': 'Rate limit exceeded. Please try again later.',
                    'retry_after': 60
                },
                status=429
            )
        
        # Check per-hour limit
        if not self.check_rate_limit(ip, 'hour', self.rate_limit_per_hour, 3600):
            logger.warning(f"Rate limit exceeded (hour) for IP: {ip}")
            return JsonResponse(
                {
                    'error': 'Hourly rate limit exceeded. Please try again later.',
                    'retry_after': 3600
                },
                status=429
            )
        
        # Check per-day limit
        if not self.check_rate_limit(ip, 'day', self.rate_limit_per_day, 86400):
            logger.warning(f"Rate limit exceeded (day) for IP: {ip}")
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

