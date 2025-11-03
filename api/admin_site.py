"""
Custom Admin Site with enhanced security
Prevents unauthorized access and provides better error handling
"""
from django.contrib import admin
from django.contrib.admin import AdminSite
from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.urls import reverse
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class SecureAdminSite(AdminSite):
    """
    Custom admin site with security enhancements
    """
    site_header = "Zenith ERP Administration"
    site_title = "Zenith ERP Admin"
    index_title = "Welcome to Zenith ERP Administration | API Docs: /api/docs/"
    
    def has_permission(self, request):
        """
        Only allow superusers to access admin panel
        """
        return (
            request.user.is_active and
            request.user.is_staff and
            request.user.is_superuser
        )
    
    def login(self, request, extra_context=None):
        """
        Custom login view with better error handling
        """
        # If user is already logged in but not superuser, redirect
        if request.user.is_authenticated:
            if not self.has_permission(request):
                return self.redirect_to_home(request)
        
        # Use default Django admin login
        return super().login(request, extra_context)
    
    def index(self, request, extra_context=None):
        """
        Custom admin index page with API documentation link
        """
        if not self.has_permission(request):
            return self.redirect_to_home(request)
        
        # Add API documentation link to context
        extra_context = extra_context or {}
        from django.urls import reverse
        try:
            api_docs_url = reverse('api-docs')
            extra_context['api_docs_url'] = request.build_absolute_uri(api_docs_url)
            extra_context['api_docs_title'] = 'API Documentation'
            extra_context['api_docs_available'] = True
        except Exception:
            extra_context['api_docs_url'] = None
            extra_context['api_docs_title'] = None
            extra_context['api_docs_available'] = False
        
        return super().index(request, extra_context)
    
    def redirect_to_home(self, request):
        """
        Redirect unauthorized users to home page or show error
        """
        # Redirect to frontend or show error page
        if hasattr(settings, 'FRONTEND_URL'):
            return HttpResponseRedirect(settings.FRONTEND_URL)
        else:
            # Show custom error page
            return TemplateResponse(
                request,
                'admin/access_denied.html',
                {
                    'site_header': self.site_header,
                    'site_title': self.site_title,
                },
                status=403
            )
    
    def each_context(self, request):
        """
        Add extra context to all admin pages
        """
        context = super().each_context(request)
        context['site_url'] = getattr(settings, 'FRONTEND_URL', '/')
        # Add API documentation link to all admin pages
        try:
            from django.urls import reverse
            context['api_docs_url'] = reverse('api-docs')
            context['api_docs_title'] = 'API Documentation'
        except Exception:
            context['api_docs_url'] = None
            context['api_docs_title'] = None
        return context
    
    def get_urls(self):
        """
        Override to add custom API docs redirect URL
        """
        from django.urls import path
        from django.contrib.admin.views.decorators import staff_member_required
        from django.shortcuts import redirect
        
        @staff_member_required
        def api_docs_admin_redirect(request):
            """Admin view to redirect to API documentation"""
            api_docs_url = reverse('api-docs')
            return redirect(api_docs_url)
        
        urls = super().get_urls()
        custom_urls = [
            path('api-docs/', api_docs_admin_redirect, name='admin-api-docs'),
        ]
        return custom_urls + urls


# Create custom admin site instance
secure_admin_site = SecureAdminSite(name='secureadmin')


def get_admin_site():
    """
    Get the secure admin site instance
    Use this to register models
    """
    return secure_admin_site

