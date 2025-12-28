"""
Defines common permissions for the daily_goals app.
"""

from rest_framework.permissions import BasePermission

AUTH_FAILURE_MESSAGE = "Forbidden"


def is_in_group(user, group_name: str, include_superuser: bool = True) -> bool:
    if include_superuser and user.is_superuser:
        return True
    user_groups = [group.name for group in user.groups.all()]
    return group_name in user_groups


class UserInDailyGoalsManagerGroup(BasePermission):
    message = AUTH_FAILURE_MESSAGE

    def has_permission(self, request, view) -> bool:
        return is_in_group(request.user, "DailyGoalsManager")


class UserInDailyGoalsWebhookCaller(BasePermission):
    message = AUTH_FAILURE_MESSAGE

    def has_permission(self, request, view) -> bool:
        return is_in_group(request.user, "DailyGoalsWebhookCaller")
