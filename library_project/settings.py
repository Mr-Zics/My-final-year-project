"""
Django settings for library_project.

Web-Based Library Management System with Automated Book Reservation
and Overdue Notifications.
BSc Computer Science Final-Year Project.
"""

from pathlib import Path
from decouple import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-university-library-project-key-2026')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=lambda v: [s.strip() for s in v.split(',')])

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    # University Library Apps
    'accounts.apps.AccountsConfig',
    'catalogue.apps.CatalogueConfig',
    'reservations.apps.ReservationsConfig',
    'circulation.apps.CirculationConfig',
    'fines.apps.FinesConfig',
    'notifications.apps.NotificationsConfig',
    'core.apps.CoreConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'library_project.urls'

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

WSGI_APPLICATION = 'library_project.wsgi.application'

# Database Configuration (MySQL 8.0, InnoDB, utf8mb4)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('DB_NAME', default='library_db'),
        'USER': config('DB_USER', default='root'),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST': config('DB_HOST', default='127.0.0.1'),
        'PORT': config('DB_PORT', default='3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES', default_storage_engine=INNODB",
        },
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization and Timezone
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Lagos'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files (Uploaded book covers, etc.)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Session Configuration: 2 hours of inactivity
SESSION_COOKIE_AGE = 7200
SESSION_SAVE_EVERY_REQUEST = True

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'login'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ==============================================================================
# Email Configuration
# ==============================================================================
# EMAIL_MODE can be 'console' (default for dev/offline) or 'smtp' (live email)
EMAIL_MODE = config('EMAIL_MODE', default='console').lower()
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=(EMAIL_PORT == 465), cast=bool)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=(EMAIL_PORT == 587 and not EMAIL_USE_SSL), cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='').replace(' ', '')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default=config('EMAIL_HOST_USER', default='noreply@unilibrary.edu.ng') or 'noreply@unilibrary.edu.ng')
EMAIL_TIMEOUT = 25

if EMAIL_MODE == 'smtp':
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ==============================================================================
# Library System Policy Constants (Simplified Final-Year Project Rules)
# Replaces database Settings table with fixed, transparent policy constants.
# ==============================================================================
LOAN_PERIOD_DAYS = 14          # Duration in days for standard borrowing
MAX_LOANS_PER_STUDENT = 3      # Maximum number of books a student may hold at once
FINE_PER_DAY = 50              # Overdue penalty in Nigerian Naira per overdue day
REMINDER_DAYS_BEFORE_DUE = 2   # Advance notice days before loan deadline
OVERDUE_REPEAT_DAYS = 3        # Interval in days between consecutive overdue notices
MAX_OVERDUE_NOTICES = 3        # Maximum overdue notices sent per overdue loan
PICKUP_WINDOW_HOURS = 48       # Hours a reserved copy is held before expiry



