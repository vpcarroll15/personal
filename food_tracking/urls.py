from django.urls import path

from food_tracking import views

app_name = "food_tracking"
urlpatterns = [
    path("", views.home, name="home"),
    path("log/", views.log_consumption, name="log_consumption"),
    path("delete/", views.delete_consumption, name="delete_consumption"),
    path("reports/", views.reports, name="reports"),
    path("estimate/", views.estimate, name="estimate"),
    path("estimate-recipe/", views.estimate_recipe, name="estimate_recipe"),
    path("log-estimate/", views.log_estimate, name="log_estimate"),
    path("log-exercise/", views.log_exercise, name="log_exercise"),
    path("target/", views.set_target, name="set_target"),
]
