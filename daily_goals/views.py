"""Views for the daily_goals app."""

from datetime import datetime
from django.http import HttpResponse, HttpResponseBadRequest
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from daily_goals.permissions import (
    UserInDailyGoalsManagerGroup,
    UserInDailyGoalsWebhookCaller,
)
from daily_goals.models import User, DailyCheckin


class DailyGoalsManagerView(APIView):
    permission_classes = [IsAuthenticated, UserInDailyGoalsManagerGroup]


class UsersView(DailyGoalsManagerView):
    def get(self, request):
        return Response(
            dict(users=[user.to_dict_for_api() for user in User.objects.all()])
        )


class UserView(DailyGoalsManagerView):
    def put(self, request):
        for key in ["last_start_text_sent_date", "last_end_text_sent_date"]:
            if key in request.data:
                request.data[key] = datetime.strptime(
                    request.data[key], "%Y-%m-%d"
                ).date()

        # Figure out if we're creating a new object...then do it.
        user_id = request.data.pop("id", None)
        if user_id is None:
            user = User.objects.create(**request.data)
        else:
            user, _ = User.objects.update_or_create(id=user_id, defaults=request.data)
        return Response(dict(user=user.to_dict_for_api()))


class DailyCheckinView(DailyGoalsManagerView):
    def post(self, request):
        checkin = DailyCheckin(**request.data)
        checkin.save()
        return Response(
            dict(checkin=checkin.to_dict_for_api()),
            status=status.HTTP_201_CREATED,
        )


class DailyGoalsWebhookView(APIView):
    permission_classes = [IsAuthenticated, UserInDailyGoalsWebhookCaller]


class NoRelevantDailyCheckinException(Exception):
    """Raise this exception when there is no relevant DailyCheckin for a phone number."""


class DailyCheckinAlreadyPopulatedException(Exception):
    """Raise this exception when a DailyCheckin is already populated with goals and there is nothing to do."""


class UnparseableMessageException(Exception):
    """Raise this exception when a message is unparseable and we can't figure out how to populate the checkin."""


def get_relevant_daily_checkin(phone_number: str) -> DailyCheckin:
    users = User.objects.filter(phone_number=phone_number)
    if len(users) != 1:
        raise NoRelevantDailyCheckinException
    user = users[0]

    daily_checkins = DailyCheckin.objects.filter(user=user).order_by("-created_at")[:1]
    if len(daily_checkins) != 1:
        raise NoRelevantDailyCheckinException
    daily_checkin = daily_checkins[0]

    if daily_checkin.chosen_focus_areas:
        raise DailyCheckinAlreadyPopulatedException

    return daily_checkin


def parse_chosen_focus_areas(body: str, checkin: DailyCheckin) -> list[str]:
    # Remove the leading "g" if it exists.
    if body.startswith("g"):
        body = body[1:]

    body_pieces = body.split(",")
    unpacked_body_pieces = []

    for piece in body_pieces:
        piece = piece.strip()
        if not piece:
            continue
        try:
            piece_index = int(piece)
        except ValueError:
            # We assume that this is a novel goal.
            unpacked_body_pieces.append(piece)
        else:
            if piece_index < 1:
                raise UnparseableMessageException
            if piece_index > len(checkin.possible_focus_areas):
                raise UnparseableMessageException
            focus_area = checkin.possible_focus_areas[piece_index - 1]
            if focus_area in unpacked_body_pieces:
                continue
            unpacked_body_pieces.append(focus_area)

    if not unpacked_body_pieces:
        raise UnparseableMessageException
    return unpacked_body_pieces


class WebhookView(DailyGoalsWebhookView):
    def post(self, request):
        """
        Example:
        http POST daily_goals/webhook/ {...(data)...}
        """
        for key in ["From", "Body"]:
            if key not in request.POST:
                return HttpResponseBadRequest(f"Missing required key: {key}")

        phone_number = request.POST["From"]
        try:
            daily_checkin = get_relevant_daily_checkin(phone_number)
        except NoRelevantDailyCheckinException:
            return HttpResponseBadRequest(
                f"No relevant DataPoint for this phone number: {phone_number}"
            )
        except DailyCheckinAlreadyPopulatedException:
            # Nothing to be done if the DataPoint is already populated, or if the
            # window of opportunity has passed. Just do nothing.
            return HttpResponse(status=204)

        body = request.POST["Body"]
        try:
            chosen_focus_areas = parse_chosen_focus_areas(body, daily_checkin)
        except UnparseableMessageException:
            # Don't do anything because this is probably just user error.
            return HttpResponse(status=204)

        daily_checkin.response_message_id = request.POST.get("MessageSid")
        daily_checkin.chosen_focus_areas = chosen_focus_areas
        daily_checkin.save()

        return HttpResponse(status=200)
