
from django.urls import path

from . import views

app_name = 'scavenger_hunt'
urlpatterns = [
    path('', views.index, name='home'),
]