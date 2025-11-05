import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file from backend directory
try:
    env_path = BASE_DIR / '.env'
    load_dotenv(dotenv_path=env_path)  # Enable environment variables loading
    import sys
    if sys.stdout.encoding and 'utf' in sys.stdout.encoding.lower():
        print(f"✅ Loaded .env from: {env_path}")
    else:
        print(f"Loaded .env from: {env_path}")
except Exception as e:
    import sys
    if sys.stdout.encoding and 'utf' in sys.stdout.encoding.lower():
        print(f"⚠️  Warning: Could not load .env file: {e}")
    else:
        print(f"Warning: Could not load .env file: {e}")
    # Continue without .env file

# ============================================
# SECURITY: SECRET_KEY must be set in environment variable
# ============================================
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    # For development, use a default but warn
    if os.getenv('DEBUG', 'True').lower() == 'true':
        SECRET_KEY = 'DEV-SECRET-KEY-CHANGE-IN-PRODUCTION-' + os.getenv('USER', 'dev')
        print("⚠️  WARNING: Using default SECRET_KEY. Set SECRET_KEY environment variable for production!")
    else:
        raise ValueError(
            "SECRET_KEY environment variable must be set! "
            "Generate one using: python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'"
        )

DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'  # Default to False for security
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if os.getenv('ALLOWED_HOSTS') else ['localhost', '127.0.0.1']
ALLOWED_HOSTS = [h.strip() for h in ALLOWED_HOSTS if h.strip()]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',
    'api',
    'corsheaders',
    'education',
    'pharmacy',
    'retail',
    'hotel',
    'restaurant',
    'salon',
    'drf_yasg',
]

# Build middleware list conditionally
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
]

# Add HTTPS handler in development, SecurityMiddleware in production
if DEBUG:
    MIDDLEWARE.append('api.middleware.development_https_handler.DevelopmentHTTPSHandlerMiddleware')
else:
    MIDDLEWARE.append('django.middleware.security.SecurityMiddleware')

# Add remaining middleware
MIDDLEWARE.extend([
    'api.middleware.security.RequestValidationMiddleware',  # Add request validation
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',  # Must come before RateLimitMiddleware
    'api.middleware.security.RateLimitMiddleware',  # Add rate limiting (after auth so request.user exists)
    'api.middleware.security.SecurityHeadersMiddleware',  # Add security headers
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Optional: Uncomment to enable docs protection middleware
    # 'api.middleware.docs_security.DocsSecurityMiddleware',  # Protect Swagger/Redoc
])

ROOT_URLCONF = 'erp.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'api', 'templates')],  # Add api/templates directory
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'erp.wsgi.application'

# Database configuration from environment variables
DATABASES = {
    'default': {
        'ENGINE': os.getenv('DB_ENGINE', 'django.db.backends.postgresql'),
        'NAME': os.getenv('DB_NAME', 'zenith_erp_db'),
        'USER': os.getenv('DB_USER', 'zenith_user'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'  # India Standard Time (IST) - Same for Maharashtra
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files configuration
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS settings - CRITICAL for security!
# In production, ALWAYS set CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_ALL_ORIGINS = DEBUG  # Only allow all origins in development
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # React dev server
    "http://127.0.0.1:3000",  # Alternative localhost
    # Add your production frontend URL(s) here when deploying
    # Example: "https://yourdomain.com", "https://www.yourdomain.com"
]
# Allow environment variable override for production
env_cors_origins = os.getenv('CORS_ALLOWED_ORIGINS', '')
if env_cors_origins:
    CORS_ALLOWED_ORIGINS.extend([origin.strip() for origin in env_cors_origins.split(',') if origin.strip()])

# Additional CORS settings for development
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
    'x-api-key',
    'x-recaptcha-token',
]

# REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
}

# JWT Settings
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': False,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JWK_URL': None,
    'LEEWAY': 0,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',
    'JTI_CLAIM': 'jti',
    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
}

# Razorpay API keys (from .env)
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

# Email Configuration (Gmail SMTP)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')  # Your Gmail address
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')  # Your Gmail app password
DEFAULT_FROM_EMAIL = os.getenv('EMAIL_HOST_USER', 'noreply@zenitherp.com')

# Frontend URL for email verification links
FRONTEND_URL = os.getenv('FRONTEND_URL', 'https://erp-frontend-lyart.vercel.app')

# ============================================
# SECURITY SETTINGS - Production Configuration
# ============================================

if not DEBUG:
    # HTTPS Security (for production)
    SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'True').lower() == 'true'
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    
    # Cookie Security (read from environment, default to False for HTTP)
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    CSRF_COOKIE_SECURE = os.getenv('CSRF_COOKIE_SECURE', 'False').lower() == 'true'
    CSRF_COOKIE_HTTPONLY = True  # Prevent JavaScript access to CSRF cookie
    SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access to session cookie
    SESSION_COOKIE_SAMESITE = 'Strict'  # Prevent CSRF attacks
    
    # Security Headers
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'  # Prevent clickjacking
    
    # HSTS (HTTP Strict Transport Security)
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    
    # Prevent information disclosure
    SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
else:
    # Development settings (less strict)
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    
    # Suppress HTTPS warning in development (optional)
    # This warning appears when accessing via https:// but server is HTTP
    # It's harmless in development - just use http:// instead

# Request size limits (prevent DoS attacks)
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000  # Prevent field exhaustion attacks

# Password validation - Enhanced security
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 12,  # Increased from default 8
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Logging configuration for security events
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'security': {
            'format': 'SECURITY: {levelname} {asctime} {pathname} {message}',
            'style': '{',
        },
    },
    'filters': {
        'suppress_https_errors': {
            '()': 'api.utils.logging_filters.SuppressHTTPSErrorsFilter',
        },
    },
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'errors.log',
            'formatter': 'verbose',
        },
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'security.log',
            'formatter': 'security',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'filters': ['suppress_https_errors'] if DEBUG else [],
        },
        'console_filtered': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'filters': ['suppress_https_errors'] if DEBUG else [],
        },
    },
    'loggers': {
        'django.security': {
            'handlers': ['security_file', 'console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django': {
            'handlers': ['file', 'console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.server': {
            'handlers': ['console'],
            'level': 'WARNING' if DEBUG else 'INFO',
            'propagate': False,
            'filters': ['suppress_https_errors'] if DEBUG else [],
        },
        'django.core.servers.basehttp': {
            'handlers': ['console_filtered'],
            'level': 'CRITICAL' if DEBUG else 'INFO',  # Suppress all but critical in dev
            'propagate': False,
            'filters': ['suppress_https_errors'] if DEBUG else [],
        },
        'basehttp': {
            'handlers': ['console_filtered'],
            'level': 'CRITICAL' if DEBUG else 'INFO',
            'propagate': False,
            'filters': ['suppress_https_errors'] if DEBUG else [],
        },
        # Catch all basehttp variations
        'django.core.servers': {
            'handlers': ['console_filtered'],
            'level': 'CRITICAL' if DEBUG else 'INFO',
            'propagate': False,
            'filters': ['suppress_https_errors'] if DEBUG else [],
        },
        'api.middleware': {
            'handlers': ['security_file', 'console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# Ensure logs directory exists
import os
logs_dir = BASE_DIR / 'logs'
os.makedirs(logs_dir, exist_ok=True)