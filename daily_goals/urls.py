from django.urls import path

from daily_goals import views

app_name = "daily_goals"
urlpatterns = [
    path("users/", view=views.UsersView.as_view(), name="users"),
]
