
from django.urls import path

from . import views

app_name = 'scavenger_hunt'
urlpatterns = [
    path('', views.list_hunt_templates, name='hunt_list'),
    path('<int:hunt_template_id>', views.hunt_template, name='hunt_template'),
]