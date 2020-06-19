
from django.urls import path

from . import views

app_name = 'scavenger_hunt'
urlpatterns = [
    path('', views.hunt_templates, name='hunt_templates'),
    path('<int:id>', views.hunt_template, name='hunt_template'),
    path('active/<int:id>', views.hunt, name='hunt'),
]