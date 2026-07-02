"""
Django settings for config project.
"""
import os
from pathlib import Path
import dj_database_url
from dotenv import load_dotenv

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-default-key-for-dev')

# تنظیم دیباگ
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

# در فایل settings.py
CSRF_TRUSTED_ORIGINS = [
    'https://sandogh-server.liara.run',
    'https://sandogh-thana.ir',
    'http://127.0.0.1:8000',  # اضافه شد برای تست لوکال
    'http://localhost:8000',  # اضافه شد برای تست لوکال
]


# Application definition

INSTALLED_APPS = [
    # --- ابزارهای حیاتی جنگو ---
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # --- ابزارهای جانبی نصب شده ---
    'rest_framework',
    'rest_framework.authtoken',    # برای ورود
    'corsheaders',
    'import_export',             
    'jalali_date',                 # تقویم شمسی
    'drf_yasg',                    # مستندات Swagger

    # --- اپلیکیشن‌های اختصاصی (فقط یک بار تعریف شده‌اند) ---
    'users.apps.UsersConfig',
    'accounting.apps.AccountingConfig',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # برای فایل‌های استاتیک در لیارا
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # اتصال به بیلد نهایی فرانت‌ند
        'DIRS': [os.path.join(BASE_DIR, 'frontend/dist')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
DATABASES = {
    'default': dj_database_url.config(
        default='sqlite:///' + os.path.join(BASE_DIR,'media','db.sqlite3'),
        conn_max_age=600
    )
}


# Password validation
AUTH_PASSWORD_VALIDATORS = []


# Internationalization
LANGUAGE_CODE = 'fa-ir'
TIME_ZONE = 'Asia/Tehran'
USE_I18N = True
USE_TZ = True
# این خط برای کارکرد صحیح کتابخانه جلالی دیت حیاتی است
USE_L10N = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'frontend/dist'),
]

# Media files (برای تصاویر واریزی)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'users.User'

# تنظیمات CORS
CORS_ALLOW_ALL_ORIGINS = True

# تنظیمات فریم‌ورک رست (API)
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# تنظیمات پیش‌فرض تاریخ شمسی
JALALI_DATE_DEFAULTS = {
   'Strftime': {
        'date': '%Y/%m/%d',
        'datetime': '%H:%M:%S _ %Y/%m/%d',
    },
    'Static': {
        'js': [ 'admin/js/django_jalali.min.js', ],
        'css': { 'all': [ 'admin/css/django_jalali.min.css', ], }
    },
}

# --- تنظیمات حیاتی برای حل مشکل ۴۰۴ در سایت‌های تک‌صفحه‌ای (SPA) ---
APPEND_SLASH = True