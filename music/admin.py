from django.contrib import admin

from .models import Tag, Music, Musician

admin.site.register(Tag)
admin.site.register(Music)
admin.site.register(Musician)
