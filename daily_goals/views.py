"""Views for the daily_goals app."""

from datetime import datetime
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from daily_goals.permissions import UserInDailyGoalsManagerGroup
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
            request.data[key] = datetime.strptime(request.data[key], "%Y-%m-%d").date()

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
