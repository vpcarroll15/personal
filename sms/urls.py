from django.urls import path

from sms import views

app_name = 'sms'
urlpatterns = [
    path("webhook/", view=views.WebhookView.as_view(), name="webhook"),
    path("users/", view=views.UsersView.as_view(), name="users"),
]
