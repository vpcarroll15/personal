from django.urls import path

from sms import views

app_name = "sms"
urlpatterns = [
    path("data_point/", view=views.DataPointView.as_view(), name="data_point"),
    path("webhook/", view=views.WebhookView.as_view(), name="webhook"),
    path("users/", view=views.UsersView.as_view(), name="users"),
    path("user/", view=views.UserView.as_view(), name="user"),
    path("home/", view=views.home, name="home"),
    path("home/question/<int:id>", view=views.question, name="question"),
    path("home/error/", view=views.error, name="error"),
]
