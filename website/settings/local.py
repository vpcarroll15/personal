from .base import *

DEBUG = True
ALLOWED_HOSTS = ['*']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'mywebsite',
        'USER': 'paul',
        'PASSWORD': os.environ['LOCAL_DB_PASSWORD'],
        'HOST': 'localhost',
        'PORT': '',
    },
}
