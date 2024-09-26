"""
Django settings for the project.

Generated by 'django-admin startproject' using Django 3.1.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/topics/settings/

For the full list of settings and their values, see
"""
import os
from pathlib import Path
from warnings import warn
from datetime import timedelta

from science.db.migrate import do_migration, new_data_staged
from science.db.sql import (MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD,
                            sql_port, DEBUG, EMAIL_HOST, EMAIL_PORT, EMAIL_USER, EMAIL_APP_PASSWORD,
                            wait_for_mysql_to_start, DATA_MIGRATE_FROM_STAGED)


if not wait_for_mysql_to_start():
    raise Exception("Could not connect to MySQL database, please check your environment variables.")
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve(strict=True).parent.parent
server_dir = BASE_DIR.parent

if DEBUG:
    warn(f"Running in DEBUG mode, this is not recommended for production.")

if DATA_MIGRATE_FROM_STAGED and new_data_staged:
    do_migration()

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY",  'a$c#ph)5yg%r)d-qp*^-vkxgfw!r$$e%%md)!r6m$$j26x(r1c')

ALLOWED_HOSTS = [
     'localhost',
     '127.0.0.1',
     '54.205.14.53',
     '35.169.66.245',
     'spexodisks.com',
     'www.spexodisks.com',
     'backend',
 ]

# Application definition

INSTALLED_APPS = [
    'drf_generators',
    'drf_multiple_model',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    "crispy_forms",
    'corsheaders',
    'rest_framework',
    'djangoAPI',
    'science',
    'ref',
    # not rendering due to this 'channels',
    'channels_redis',
    'dpd_static_support',
    'django_rest_passwordreset',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'build')],
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

WSGI_APPLICATION = 'core.wsgi.application'

# Database
data_auth = {
    'ENGINE': 'django.db.backends.mysql',
    'USER': MYSQL_USER,
    'PASSWORD': MYSQL_PASSWORD,
    'PORT': sql_port,
    'HOST': MYSQL_HOST,
}
DATABASES = {
    'default': {
        'NAME': 'users',
        **data_auth,
    },
    'spectra': {
        'NAME': 'spectra',
        **data_auth,
    },
    'spexodisks': {
        'NAME': 'spexodisks',
        **data_auth,
    },
    'new_spectra': {
        'NAME': 'new_spectra',
        **data_auth,
    },
    'new_spexodisks': {
        'NAME': 'new_spexodisks',
        **data_auth,
    }

}

# Password validation
# https://docs.djangoproject.com/en/3.1/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/3.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.1/howto/static-files/

STATIC_URL = '/api/static/'
STATICFILES_DIRS = []
STATIC_ROOT = os.path.join(BASE_DIR, 'static_root')

MEDIA_URL = '/api/images/'

## ENABLE USE OF FRAMES WITHIN HTML DOCUMENTS PLOTLY
X_FRAME_OPTIONS = 'SAMEORIGIN'
# X_FRAME_OPTIONS = 'ALLOW-FROM localhost:8000'

# ROUTING FOR CHANNELS ETC.
ASGI_APPLICATION = 'matplot.routing.application'
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [('127.0.0.1', 6379), ],
        }
    }
}
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

# Cross-Origin Resource Sharing (CORS) settings
CORS_ORIGIN_ALLOW_ALL = False
CORS_ORIGIN_WHITELIST = (
    'https://spexodisks.com',
    'https://www.spexodisks.com',
    'http://localhost:3000',
    'http://localhost',
    'http://127.0.0.1',
    'http://127.0.0.1:3000',
    'http://54.205.14.53',
    'http://35.169.66.245'

)
# this is CORS for POST requests
CSRF_TRUSTED_ORIGINS = [
]

# Email server Configuration
# DJANGO_EMAIL_APP_PASSWORD, NOTE THIS IS A DIFFERENT PASSWORD COMPARED TO LOGGING IN W/ EMAIL
if EMAIL_USER:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = EMAIL_HOST
    EMAIL_USE_TLS = True
    EMAIL_USE_SSL = False
    EMAIL_PORT = EMAIL_PORT
    EMAIL_HOST_USER = EMAIL_USER
    EMAIL_HOST_PASSWORD = EMAIL_APP_PASSWORD
else:
    warn("Email server not configured, please set the environment variables DJANGO_EMAIL_USER and DJANGO_EMAIL_APP_PASSWORD")

# USER AUTHENTICATION FOR SIGNUP AND LOGIN
AUTH_USER_MODEL = 'djangoAPI.UserAccount'

DOMAIN = 'localhost:3000'
SITE_NAME = 'SpExoDisks'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.ScopedRateThrottle',
        'core.throttling.BurstRateThrottle',
        'core.throttling.SustainedRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'spectra': '5/min',
        'burst': '25/min',
        'sustained': '5000/day'
    }
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=90),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': False,
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# When set to True, if the request URL does not match any of the patterns in the URLconf, it will
# try appending a slash to the request path and try again. If it finds a match, the function will
APPEND_SLASH = True
