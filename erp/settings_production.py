"""
Production Settings for Render + Supabase
Import this in wsgi.py or use with --settings flag for production
"""
from .settings import *
import os
import dj_database_url

# Force production settings
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
SECRET_KEY = os.getenv('SECRET_KEY', 'replace-this-with-a-secure-key')

# Allowed hosts - filter out empty strings
allowed_hosts_env = os.getenv('ALLOWED_HOSTS', '')
ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_env.split(',') if host.strip()]
# If no allowed hosts set, default to api domain
if not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ['api.zenitherp.online', 'zenitherp.online']

# Database Configuration - Supports Supabase DATABASE_URL
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL:
    # Parse DATABASE_URL (Supabase format)
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600)
    }
else:
    # Fallback to individual database settings
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME', 'postgres'),
            'USER': os.getenv('DB_USER', 'postgres'),
            'PASSWORD': os.getenv('DB_PASSWORD', ''),
            'HOST': os.getenv('DB_HOST', 'localhost'),
            'PORT': os.getenv('DB_PORT', '5432'),
        }
    }

# Security Settings (Production)
SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'True').lower() == 'true'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Cookie Security (HTTPS only in production)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'

# Security Headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# HSTS (HTTP Strict Transport Security)
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# CORS - Must be configured for production
# Override base settings to ensure production CORS is used
CORS_ALLOW_ALL_ORIGINS = False  # Never allow all in production!
# Get CORS origins from environment variable, filter out empty strings
cors_origins_env = os.getenv('CORS_ALLOWED_ORIGINS', '')
CORS_ALLOWED_ORIGINS = [origin.strip() for origin in cors_origins_env.split(',') if origin.strip()]

# If no CORS origins are set, log a warning (but don't break the app)
if not CORS_ALLOWED_ORIGINS:
    import logging
    logger = logging.getLogger(__name__)
    logger.warning("⚠️ CORS_ALLOWED_ORIGINS is not set! API requests from frontend will fail. Set CORS_ALLOWED_ORIGINS environment variable with comma-separated frontend URLs.")
else:
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"✅ CORS configured with {len(CORS_ALLOWED_ORIGINS)} allowed origin(s): {', '.join(CORS_ALLOWED_ORIGINS)}")

# Additional CORS settings
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# Static files with whitenoise
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files (if using cloud storage, configure here)
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

# Disable development-specific features
# The runserver command should not be used in production