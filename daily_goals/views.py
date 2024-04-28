"""Views for the daily_goals app."""

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from daily_goals.permissions import UserInDailyGoalsManagerGroup
from daily_goals.models import User


class DailyGoalsManagerView(APIView):
    permission_classes = [IsAuthenticated, UserInDailyGoalsManagerGroup]


class UsersView(DailyGoalsManagerView):
    def get(self, request):
        return Response(
            dict(users=[user.to_dict_for_api() for user in User.objects.all()])
        )
