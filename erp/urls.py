
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.http import HttpResponseRedirect
from rest_framework import permissions
from rest_framework.permissions import IsAuthenticated
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from api.admin_site import secure_admin_site

# Only allow authenticated users to access API docs in production
docs_permission = permissions.AllowAny if settings.DEBUG else IsAuthenticated

schema_view = get_schema_view(
    openapi.Info(
        title="Zenith ERP API",
        default_version='v1',
        description="API documentation for the Zenith ERP system. Authentication required.",
    ),
    public=False,  # Don't expose publicly
    permission_classes=(docs_permission,),
)

def redirect_admin(request):
    """Redirect to secure admin or show access denied"""
    if request.user.is_authenticated and request.user.is_superuser:
        return HttpResponseRedirect('/secure-admin/')
    else:
        # Show access denied page
        return TemplateView.as_view(template_name='admin/access_denied.html')(request)

urlpatterns = [
    # Old admin path - redirect to secure admin or show error
    path('admin/', redirect_admin, name='admin-redirect'),
    # Secure admin path (only accessible to superusers)
    path('secure-admin/', secure_admin_site.urls),
    path('api/', include('api.urls')),
    # Protected API documentation (requires authentication in production)
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('api-docs/', schema_view.with_ui('redoc', cache_timeout=0), name='api-docs'),  # Alias
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
