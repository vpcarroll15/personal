from django.contrib import admin

from .models import PrayerSchema, PrayerSnippet


class PrayerSnippetAdmin(admin.ModelAdmin):
    # Exclude this because it loads way too many fields.
    exclude = ["sms_data_point"]


admin.site.register(PrayerSnippet, PrayerSnippetAdmin)


admin.site.register(PrayerSchema)
