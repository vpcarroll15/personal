"""Views for the sms app."""

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from twilio.twiml.messaging_response import MessagingResponse

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
        resp = MessagingResponse()
        resp.message("The Robots are coming! Head for the hills!")
        return Response(str(resp))
