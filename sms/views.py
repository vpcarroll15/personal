"""Views for the sms app."""

from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from sms.permissions import UserInSmsManagerGroup, UserInSmsWebhookCaller
from sms.models import User


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


class WebhookView(SmsWebhookView):
    def post(self, request):
        """
        Example:
        http POST sms/webhook/ {...(data)...}
        """
        # TODO: Replace this with something that isn't horrific.
        with open("/tmp/testfile.txt", "w") as testfile:
            testfile.write(repr(request))
        # Return a blank response to the webhook. We don't have any commands for Twilio
        # at this time, but we want it to know that everything worked as expected.
        return HttpResponse(status=204)
