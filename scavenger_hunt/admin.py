from django.contrib import admin

from .models import ScavengerHunt, ScavengerHuntTemplate, Location


class ScavengerHuntAdmin(admin.ModelAdmin):
    list_display = ('hunt', 'current_location', 'updated_at')


admin.site.register(ScavengerHunt, ScavengerHuntAdmin)


class ScavengerHuntTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'updated_at')


admin.site.register(ScavengerHuntTemplate, ScavengerHuntTemplateAdmin)


class LocationAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'updated_at')


admin.site.register(Location, LocationAdmin)
