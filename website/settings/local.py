from .base import *

DEBUG = True
ALLOWED_HOSTS = ['*']
DATABASES['default'] = DATABASES['local']
