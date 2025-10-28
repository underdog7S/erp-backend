import os
from pathlib import Path
from dotenv import load_dotenv

# load_dotenv()  # temporarily commented out

BASE_DIR = Path(__file__).resolve().parent.parent

# Security settings for production
SECRET_KEY = os.getenv('SECRET_KEY', 'replace-this-with-a-secure-key')
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    'erp-backend-av9v.onrender.com',  # Your Render backend domain
]
# Also allow environment variable override
env_hosts = os.getenv('ALLOWED_HOSTS', '').split(',')
if env_hosts and env_hosts[0].strip():
    ALLOWED_HOSTS.extend([
        host.strip() for host in env_hosts
        if host.strip() and host.strip() not in ALLOWED_HOSTS
    ])

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
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

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    # 'whitenoise.middleware.WhiteNoiseMiddleware',  # Temporarily disabled
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'erp.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

# Database - Supabase PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('SUPABASE_DB_NAME', 'postgres'),
        'USER': os.getenv('SUPABASE_DB_USER', 'postgres.xbemjxfunalbebxwoffz'),
        'PASSWORD': os.getenv('SUPABASE_DB_PASSWORD', ''),
        'HOST': os.getenv('SUPABASE_DB_HOST', 'aws-1-ap-southeast-1.pooler.supabase.com'),
        'PORT': os.getenv('SUPABASE_DB_PORT', '6543'),
        'OPTIONS': {
            'sslmode': 'require',
        },
    }
}

# Password validation
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

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
# STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'  # Temporarily disabled

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS settings for production
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'https://erp-backend-av9v.onrender.com',  # Your Render backend URL
]
# Also allow environment variable override
env_origins = os.getenv('CORS_ALLOWED_ORIGINS', '').split(',')
if env_origins and env_origins[0].strip():
    CORS_ALLOWED_ORIGINS.extend([
        origin.strip() for origin in env_origins
        if origin.strip() and origin.strip() not in CORS_ALLOWED_ORIGINS
    ])
CORS_ALLOW_CREDENTIALS = True

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# JWT Settings
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
}

# Email settings
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')

# Frontend URL for email verification links
FRONTEND_URL = os.getenv('FRONTEND_URL', 'https://erp-frontend-lyart.vercel.app')

# Razorpay settings
RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID', '')
RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET', '')

# Google OAuth settings
GOOGLE_OAUTH_CLIENT_ID = os.getenv('GOOGLE_OAUTH_CLIENT_ID', '')
GOOGLE_OAUTH_CLIENT_SECRET = os.getenv('GOOGLE_OAUTH_CLIENT_SECRET', '')
GOOGLE_OAUTH_REDIRECT_URI = os.getenv('GOOGLE_OAUTH_REDIRECT_URI', '')

# Tawk.to settings
TAWK_SITE_ID = os.getenv('TAWK_SITE_ID', '')
TAWK_WIDGET_ID = os.getenv('TAWK_WIDGET_ID', '')

# Supabase settings
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://xbemjxfunalbebxwoffz.supabase.co')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY', '')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY', '')

# CSRF settings for production
CSRF_TRUSTED_ORIGINS = [
    'https://erp-backend-av9v.onrender.com',
    'https://erp-frontend-psi-six.vercel.app',
    'http://localhost:3000',
    'http://127.0.0.1:3000',
]

# Security settings for production
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
