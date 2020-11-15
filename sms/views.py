"""Views for the sms app."""

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from sms.permissions import UserInSmsManagerGroup, UserInSmsWebhookCaller


class SmsManagerView(APIView):
    permission_classes = [IsAuthenticated, UserInSmsManagerGroup]


class SmsWebhookView(APIView):
    permission_classes = [IsAuthenticated, UserInSmsWebhookCaller]

    def post(self, request):
        """
        Example:
        http POST sms/webhook/ {...(data)...}
        """
        # TODO: Replace this with something that isn't horrific.
        with open("/tmp/testfile.txt", "w") as testfile:
            testfile.write(repr(request))
        return Response(dict(success=True))
