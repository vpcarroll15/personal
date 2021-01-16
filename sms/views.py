"""Views for the sms app."""

from datetime import datetime, timezone
import dateutil.parser

from django.contrib.auth.decorators import login_required
from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseNotAllowed,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
import pytz
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from sms.permissions import UserInSmsManagerGroup, UserInSmsWebhookCaller
from sms.models import User, DataPoint, Question


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

    if (
        datetime.now(tz=timezone.utc) - data_point.created_at
        > user.expire_message_after
    ):
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
        return Response(
            dict(users=[user.to_dict_for_api() for user in User.objects.all()])
        )


class UserView(SmsManagerView):
    def put(self, request):
        # Clean up request.data.
        request.data.pop("questions", None)
        if "send_message_at_time" in request.data:
            request.data["send_message_at_time"] = dateutil.parser.parse(
                request.data["send_message_at_time"]
            )

        # Figure out if we're creating a new object...then do it.
        user_id = request.data.pop("id", None)
        if user_id is None:
            user = User.objects.create(**request.data)
        else:
            user, _ = User.objects.update_or_create(id=user_id, defaults=request.data)
        return Response(dict(user=user.to_dict_for_api()))


class DataPointView(SmsManagerView):
    def post(self, request):
        data_point = DataPoint(**request.data)
        data_point.save()
        return Response(
            dict(data_point=data_point.to_dict_for_api()),
            status=status.HTTP_201_CREATED,
        )


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
            return HttpResponseBadRequest(
                f"No relevant DataPoint for this phone number: {phone_number}"
            )
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


class TooManySmsUsersException(Exception):
    """An exception that we throw if one logged_in_user is
    associated with more than one SMS user."""


def get_sms_account(logged_in_user):
    """Returns the SMS user, given the logged-in user.
    
    Throws TooManySmsUsersException is more than one SMS
    user is somehow associated with a particular account.
    May return None."""
    sms_users = logged_in_user.user_set.all()
    num_sms_users = sms_users.count()
    if not num_sms_users:
        return None
    if num_sms_users > 1:
        raise TooManySmsUsersException
    return sms_users[0]


def has_valid_sms_account(logged_in_user):
    """Returns if the user has a valid account for seeing their SMSs."""
    try:
        sms_user = get_sms_account(logged_in_user)
    except TooManySmsUsersException:
        return False
    return sms_user is not None


@login_required
def question(request, id):
    """Renders a single question detailed view."""
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])

    question = get_object_or_404(Question, pk=id)
    if not has_valid_sms_account(request.user):
        url = reverse("sms:error")
        return redirect(url)
    return render(request, "sms/question.html", {"question": question})


@login_required
def home(request):
    """Renders either a list of questions that might be relevant to the
    user, or redirects to the single question applying to the user
    for convenience."""
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])

    error_url = reverse("sms:error")
    if not has_valid_sms_account(request.user):
        return redirect(error_url)

    sms_account = get_sms_account(request.user)
    questions = sms_account.questions.all()
    num_questions = questions.count()

    if not num_questions:
        return redirect(error_url)

    # Special case for convenience! If the user only cares about one
    # question, redirect them directly to that page.
    if num_questions == 1:
        url = reverse("sms:question", kwargs={"id": questions[0].id})
        return redirect(url)

    return render(request, "sms/questions.html", {"questions": list(questions)})


def error(request):
    """Renders an error view for the user."""
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    return render(request, "sms/error.html")


@login_required
def data_points(request):
    """Returns a JSON object consisting of a serialized list of DataPoints.
    
    Required params: question_id, parseable as int
    Optional params:
        - start_date (inclusive): in the format 2017-12-31
        - end_date (noninclusive): in the format 2017-12-31
    """
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])

    error_url = reverse("sms:error")
    if not has_valid_sms_account(request.user):
        return redirect(error_url)

    sms_account = get_sms_account(request.user)

    local_time = pytz.timezone(sms_account.timezone)

    def to_local_time(time_str):
        if time_str is None:
            localized_time = None
        else:
            localized_time = local_time.localize(
                datetime.strptime(time_str, "%Y-%m-%d")
            )
        return localized_time

    try:
        question_id = int(request.GET["question_id"])
        start_datetime = to_local_time(request.GET.get("start_date"))
        end_datetime = to_local_time(request.GET.get("end_date"))
    except (KeyError, ValueError):
        return HttpResponse(reason="Invalid input to GET", status=400)

    data_points = DataPoint.objects.filter(user=sms_account, question_id=question_id)
    if start_datetime is not None:
        data_points = data_points.filter(created_at__gte=start_datetime)
    if end_datetime is not None:
        data_points = data_points.filter(created_at__lt=end_datetime)
    data_points = data_points.exclude(score=None)
    data_points = data_points.order_by('id')

    return JsonResponse(
        {"data_points": [data_point.to_dict_for_api() for data_point in data_points]}
    )
