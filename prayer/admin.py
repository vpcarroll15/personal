from django.contrib import admin

from .models import PrayerSchema, PrayerSnippet


admin.site.register(PrayerSchema)
admin.site.register(PrayerSnippet)
