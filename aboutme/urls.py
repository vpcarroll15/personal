from django.urls import path

from . import views

app_name = 'aboutme'
urlpatterns = [
    path('', views.aboutme, name='home'),
]
