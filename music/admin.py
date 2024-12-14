from django.contrib import admin

from .models import Tag, Music, Musician, BestOf


class MusicianAdmin(admin.ModelAdmin):
    ordering = ["name"]


class TagAdmin(admin.ModelAdmin):
    ordering = ["name"]


admin.site.register(Tag, TagAdmin)
admin.site.register(Music)
admin.site.register(Musician, MusicianAdmin)
admin.site.register(BestOf)
