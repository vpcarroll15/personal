"""Views for the sms app."""

from datetime import datetime, timezone

from django.http import HttpResponse, HttpResponseBadRequest
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from sms.permissions import UserInSmsManagerGroup, UserInSmsWebhookCaller
from sms.models import User, DataPoint


class NoRelevantDataPointException(Exception):
    pass


class DataPointAlreadyPopulatedException(Exception):
    pass


class ResponseToTextTooOld(Exception):
    pass


class UnparseableMessageException(Exception):
    pass


def get_relevant_data_point(phone_number_str):
    users = User.objects.filter(phone_number=phone_number_str)
    if len(users) != 1:
        raise NoRelevantDataPointException
    user = users[0]

    data_points = DataPoint.objects.filter(user=user).order_by("-created_at")[:1]
    if len(data_points) != 1:
        raise NoRelevantDataPointException
    data_point = data_points[0]

    if datetime.now(tz=timezone.utc) - data_point.created_at > user.expire_message_after:
        raise ResponseToTextTooOld

    if data_point.score is not None or data_point.text is not None:
        raise DataPointAlreadyPopulatedException
    return data_point


def parse_message_body(message_body_str, reference_question):
    message_body = message_body_str.split()
    if not message_body:
        raise UnparseableMessageException
    try:
        score = int(message_body[0])
    except ValueError:
        raise UnparseableMessageException
    
    if score < reference_question.min_score or score > reference_question.max_score:
        raise UnparseableMessageException

    return score, " ".join(message_body[1:])


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
        for key in ["From", "Body"]:
            if key not in request.POST:
                return HttpResponseBadRequest(f"Missing required key: {key}")

        phone_number = request.POST["From"]
        try:
            data_point = get_relevant_data_point(phone_number)
        except NoRelevantDataPointException:
            return HttpResponseBadRequest(f"No relevant DataPoint for this phone number: {phone_number}")
        except (DataPointAlreadyPopulatedException, ResponseToTextTooOld):
            # Nothing to be done if the DataPoint is already populated, or if the
            # window of opportunity has passed. Just do nothing.
            return HttpResponse(status=204)

        body = request.POST["Body"]
        try:
            score, text = parse_message_body(body, data_point.question)
        except UnparseableMessageException:
            # Don't do anything because this is probably just user error.
            return HttpResponse(status=204)
        
        data_point.response_message_id = request.POST.get("MessageSid")
        data_point.score = score
        data_point.text = text
        data_point.save()

        return HttpResponse(status=200)
