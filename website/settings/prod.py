from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# https://docs.djangoproject.com/en/2.2/ref/settings/#std:setting-ALLOWED_HOSTS
ALLOWED_HOSTS = [".paulcarroll.site", "localhost", "44.230.244.94"]

# https://docs.djangoproject.com/en/2.2/ref/middleware/#x-xss-protection-1-mode-block
SECURE_BROWSER_XSS_FILTER = True

# https://docs.djangoproject.com/en/2.2/ref/clickjacking/#preventing-clickjacking
X_FRAME_OPTIONS = "DENY"

# https://docs.djangoproject.com/en/2.2/ref/settings/#std:setting-SESSION_COOKIE_SECURE
SESSION_COOKIE_SECURE = True

# https://docs.djangoproject.com/en/2.2/ref/settings/
CSRF_COOKIE_SECURE = True

# https://docs.djangoproject.com/en/2.2/ref/settings/#std:setting-SECURE_HSTS_SECONDS
SECURE_HSTS_SECONDS = 60 * 60
SECURE_HSTS_INCLUDE_SUBDOMAINS = True

# https://django-secure.readthedocs.io/en/latest/settings.html#secure-content-type-nosniff
SECURE_CONTENT_TYPE_NOSNIFF = True

SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_PRELOAD = True

# obfuscation!
ADMINS = [("Paul", "vpcarroll15@" + "gmail.com")]
MANAGERS = [("Paul", "vpcarroll15@" + "gmail.com")]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["RDS_DB_NAME"],
        "USER": os.environ["RDS_USERNAME"],
        "PASSWORD": os.environ["RDS_PASSWORD"],
        "HOST": os.environ["RDS_HOSTNAME"],
        "PORT": os.environ["RDS_PORT"],
    },
}

DEFAULT_FROM_EMAIL = "vpcarroll15@gmail.com"
EMAIL_BACKEND = 'django_ses.SESBackend'
AWS_SES_REGION_NAME = 'us-west-2'
AWS_SES_REGION_ENDPOINT = 'email.us-west-2.amazonaws.com'
USE_SES_V2 = True
