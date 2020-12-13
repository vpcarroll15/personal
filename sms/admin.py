"""Basic admin pages for the app."""
from django.contrib import admin

from .models import User, Question, DataPoint

admin.site.register(User)
admin.site.register(Question)
admin.site.register(DataPoint)
