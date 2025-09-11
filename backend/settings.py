"""
Django settings for backend project.
"""

import os
from pathlib import Path
from datetime import timedelta

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent

# Security
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-development-key')
DEBUG = os.getenv('DEBUG', 'True') == 'True'
# FIXED ALLOWED_HOSTS - FORCE INCLUDE host.docker.internal
allowed_hosts_env = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,172.17.163.86,172.25.14.234').split(',')
ALLOWED_HOSTS = allowed_hosts_env + ['host.docker.internal']  # Force add host.docker.internal
SESSION_ENGINE = 'django.contrib.sessions.backends.db'  # Already default
SESSION_COOKIE_AGE = 86400  # 24

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'django_filters',
    'drf_yasg',
    
    # Local apps
    'authentication.apps.AuthenticationConfig',
]

# FIXED MIDDLEWARE - CSRF DISABLED FOR API
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware',  # DISABLED FOR API
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

WSGI_APPLICATION = 'backend.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'blockchain_vote'),
        'USER': os.getenv('DB_USER', 'blockchain_user'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'root'),
        'HOST': os.getenv('DB_HOST', 'db'),
        'PORT': os.getenv('DB_PORT', '5432'),
        'OPTIONS': {
            'connect_timeout': 30,
        },
    }
}

# Authentication
AUTH_USER_MODEL = 'authentication.User'
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# REST Framework - UPDATED FOR TOKEN AUTH ONLY
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        # 'rest_framework.authentication.SessionAuthentication',  # REMOVED TO AVOID CSRF
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/day',
        'user': '1000/day'
    },
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend'
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20
}

# CORS - FIXED FOR API CALLS
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://localhost:8000",
    "http://172.17.163.86:5173",  # Your actual frontend URL
    "http://172.17.163.86:8001",  # Your backend URL
    "http://host.docker.internal:5173",
    "http://host.docker.internal:8001",
]

CORS_ALLOW_CREDENTIALS = True

# CSRF COMPLETELY DISABLED FOR API-ONLY BACKEND
CSRF_TRUSTED_ORIGINS = []  # Not needed since CSRF is disabled
CSRF_COOKIE_SECURE = False
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_USE_SESSIONS = False

# Keep CORS strict for security
CORS_ALLOW_ALL_ORIGINS = True  # TEMPORARY - CHANGE TO False IN PRODUCTION
CORS_ALLOWED_HEADERS = [
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

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Email (for password reset, etc.)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'  # Change for production

# Blockchain Configuration
BLOCKCHAIN_CONFIG = {
    # Ethereum Configuration - UNCHANGED
    'ETHEREUM': {
        'PROVIDER_URL': 'http://localhost:8545',  # Ganache
        'CHAIN_ID': 1337
    },
    
    # Hyperledger Fabric Configuration - FIXED FOR DOCKER-WSL CONNECTIVITY
    'HYPERLEDGER': {
        'FABRIC_PATH': '/opt/fabric-samples',
        'NETWORK_PATH': '/opt/fabric-samples/test-network',
        'CHANNEL_NAME': 'mychannel',
        'CHAINCODE_NAME': 'voting',
        'ORDERER_URL': 'host.docker.internal:7050',
        'PEER_URL': 'host.docker.internal:7051',
        'WSL_IP': os.getenv('WSL_IP', '172.28.112.1'),
    },
    
    # IPFS Configuration - UNCHANGED
    'IPFS': {
        'HOST': os.getenv('IPFS_HOST', '/ip4/127.0.0.1/tcp/5001'),
        'TIMEOUT': 30,
    },
    
    # Metamask Configuration - UNCHANGED
    'METAMASK': {
        'NETWORK_ID': 1337,  # Ganache default
        'NETWORK_NAME': 'Ganache',
        'RPC_URL': 'http://localhost:7545',
    }
}

# Security (for production)
if not DEBUG:
    SECURE_HSTS_SECONDS = 3600
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'