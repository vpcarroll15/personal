"""Basic admin pages for the app."""
from django.contrib import admin

from .models import User, DailyCheckin

admin.site.register(User)
admin.site.register(DailyCheckin)
