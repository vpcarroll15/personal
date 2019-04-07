from django.urls import path

from . import views

app_name = 'music'
urlpatterns = [
    path('', views.home, name='home'),
    path('music/<int:music_id>', views.music, name="music_detailed")
]
