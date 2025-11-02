"""
Development HTTPS Handler Middleware
Redirects HTTPS requests to HTTP in development to prevent errors
"""
from django.conf import settings
from django.http import HttpResponsePermanentRedirect
import logging

logger = logging.getLogger(__name__)


class DevelopmentHTTPSHandlerMiddleware:
    """
    Middleware to handle HTTPS requests in development
    Redirects HTTPS to HTTP when DEBUG=True
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Only redirect in development mode
        if settings.DEBUG and request.scheme == 'https':
            # Redirect HTTPS to HTTP
            http_url = request.build_absolute_uri().replace('https://', 'http://')
            logger.info(f"Redirecting HTTPS to HTTP in development: {http_url}")
            return HttpResponsePermanentRedirect(http_url)
        
        return self.get_response(request)

