"""Views for the sms app."""

from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from sms.permissions import UserInSmsManagerGroup, UserInSmsWebhookCaller
from sms.models import User, DataPoint


class SmsManagerView(APIView):
    permission_classes = [IsAuthenticated, UserInSmsManagerGroup]


class SmsWebhookView(APIView):
    permission_classes = [IsAuthenticated, UserInSmsWebhookCaller]


class UsersView(SmsManagerView):
    def get(self, request):
        # For now, when the SMS manager requests the users to manage, just return
        # all the users. At some point this in theory wouldn't be scalable...but
        # we'll never reach that point.
        return Response(dict(users=[user.to_dict_for_api() for user in User.objects.all()]))


class DataPointView(SmsManagerView):
    def post(self, request):
        data_point = DataPoint(**request.data)
        data_point.save()
        return Response(dict(data_point=data_point.to_dict_for_api()),
                        status=status.HTTP_201_CREATED)


class WebhookView(SmsWebhookView):
    def post(self, request):
        """
        Example:
        http POST sms/webhook/ {...(data)...}
        """
        id = request["MessageSid"]
        # Return a blank response to the webhook. We don't have any commands for Twilio
        # at this time, but we want it to know that everything worked as expected.
        return HttpResponse(status=204)
