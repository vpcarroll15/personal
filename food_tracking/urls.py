from django.urls import path

from food_tracking import views

app_name = "food_tracking"
urlpatterns = [
    path("", views.home, name="home"),
    path("log/", views.log_consumption, name="log_consumption"),
    path("delete/", views.delete_consumption, name="delete_consumption"),
    path("reports/", views.reports, name="reports"),
]
