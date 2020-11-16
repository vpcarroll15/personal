"""Views for the sms app."""

from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from sms.permissions import UserInSmsManagerGroup, UserInSmsWebhookCaller
from sms.models import User, DataPoint


def get_relevant_data_point(phone_number_str):
    raise NotImplementedError


def parse_message_body(message_body_str):
    return 0, ""


def validate_score(reference_question, score):
    raise NotImplementedError


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
        # TODO(vpcarroll): Try/catch something here.
        # If we fail, return a blank response to the webhook.
        data_point = get_relevant_data_point(request.POST["From"])
        score, note = parse_message_body(request.POST["Body"])
        validate_score(data_point.question, score)
        
        data_point.response_message_id = request.POST.get("MessageSid")
        data_point.score = score
        data_point.note = note
        data_point.save()

        return HttpResponse(status=200)
