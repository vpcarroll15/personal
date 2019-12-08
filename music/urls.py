from django.urls import path

from . import views

app_name = 'music'
urlpatterns = [
    path('', views.home, name='home'),
    path('music/<int:music_id>', views.music, name="music_detailed"),
    path('search', views.search, name="search"),
    path('ratings', views.ratings, name="ratings"),
    path('rss', views.rss, name="rss"),
    path('best_of', views.best_of, name="best_of"),
]
