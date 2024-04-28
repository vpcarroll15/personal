from django.urls import path

from daily_goals import views

app_name = "daily_goals"
urlpatterns = [
    path("checkin/", view=views.DailyCheckinView.as_view(), name="checkin"),
    path("users/", view=views.UsersView.as_view(), name="users"),
    path("user/", view=views.UserView.as_view(), name="user"),
    path("webhook/", view=views.WebhookView.as_view(), name="webhook"),
]
