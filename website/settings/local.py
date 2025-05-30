from .base import *

DEBUG = True
ALLOWED_HOSTS = ["*"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "ebdb",
        "USER": "paul",
        "PASSWORD": os.environ["LOCAL_DB_PASSWORD"],
        "HOST": "localhost",
        "PORT": "",
    },
}
