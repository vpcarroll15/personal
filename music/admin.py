from django.contrib import admin

from .models import Tag, Music, Musician, BestOf

admin.site.register(Tag)
admin.site.register(Music)
admin.site.register(Musician)
admin.site.register(BestOf)
