from django.contrib import admin

from .models import BestOf, Music, Musician, Tag


class MusicianAdmin(admin.ModelAdmin):
    """Admin interface for musicians, ordered alphabetically by name."""

    ordering = ["name"]


class TagAdmin(admin.ModelAdmin):
    """Admin interface for tags, ordered alphabetically by name."""

    ordering = ["name"]


admin.site.register(Tag, TagAdmin)
admin.site.register(Music)
admin.site.register(Musician, MusicianAdmin)
admin.site.register(BestOf)
