"""
Production Settings Override
Import this in wsgi.py or use with --settings flag for production
"""
from .settings import *
import os

# Force production settings
DEBUG = False

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
CORS_ALLOW_ALL_ORIGINS = False  # Never allow all in production!
# Set CORS_ALLOWED_ORIGINS in environment variable

# Disable development-specific features
# The runserver command should not be used in production
