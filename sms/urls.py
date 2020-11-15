from django.urls import path

from sms import views

app_name = 'sms'
urlpatterns = [
    path("webhook/", view=views.SmsWebhookView.as_view(), name="webhook"),
]
