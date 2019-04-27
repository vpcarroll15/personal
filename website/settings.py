"""
Django settings for website project.

Generated by 'django-admin startproject' using Django 2.2.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.2/ref/settings/
"""

import os

# Settings that I expect to set...
PRODUCTION = False
# end

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRET_KEY = os.environ['SECRET_KEY']

if PRODUCTION:
    # SECURITY WARNING: don't run with debug turned on in production!
    DEBUG = False

    # https://docs.djangoproject.com/en/2.2/ref/settings/#std:setting-ALLOWED_HOSTS
    ALLOWED_HOSTS = ['localhost', '127.0.0.1', '.paulcarroll.site']

    # https://docs.djangoproject.com/en/2.2/ref/middleware/#x-xss-protection-1-mode-block
    SECURE_BROWSER_XSS_FILTER = True

    # https://docs.djangoproject.com/en/2.2/ref/clickjacking/#preventing-clickjacking
    X_FRAME_OPTIONS = "DENY"

    # https://docs.djangoproject.com/en/2.2/ref/settings/#std:setting-SESSION_COOKIE_SECURE
    SESSION_COOKIE_SECURE = True

    # https://docs.djangoproject.com/en/2.2/ref/settings/
    CSRF_COOKIE_SECURE = True

    # TODO: Make this longer once we believe that https works...
    # https://docs.djangoproject.com/en/2.2/ref/settings/#std:setting-SECURE_HSTS_SECONDS
    # SECURE_HSTS_SECONDS = 60
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True

    # https://django-secure.readthedocs.io/en/latest/settings.html#secure-content-type-nosniff
    SECURE_CONTENT_TYPE_NOSNIFF = True

    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_PRELOAD = True

    # obfuscation!
    ADMINS = [('Paul', 'vpcarroll15@' + 'gmail.com')]
    MANAGERS = [('Paul', 'vpcarroll15@' + 'gmail.com')]
else:
    DEBUG = True
    ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    'music.apps.MusicConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
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

ROOT_URLCONF = 'website.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'music/templates/music')],
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

WSGI_APPLICATION = 'website.wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}


# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/

STATIC_URL = '/static/'
