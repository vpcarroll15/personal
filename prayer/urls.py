from django.urls import path

from prayer import views

app_name = "prayer"
urlpatterns = [
    path("trigger/", view=views.EmailTriggererView.as_view(), name="trigger"),
]
