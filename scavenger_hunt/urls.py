from django.urls import path

from . import views

app_name = "scavenger_hunt"
urlpatterns = [
    path("", views.hunt_templates, name="hunt_templates"),
    path("<int:id>", views.hunt_template, name="hunt_template"),
    path(
        "<int:template_id>/instantiate", views.create_new_hunt, name="create_new_hunt"
    ),
    path("active/<int:id>", views.hunt, name="hunt"),
    path("active/<int:id>/heading", views.hunt_heading, name="heading"),
]
