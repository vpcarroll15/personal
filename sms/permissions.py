"""
Defines common permissions for the SMS app. These will be consumed by sms.views.
"""

from rest_framework.permissions import BasePermission


AUTH_FAILURE_MESSAGE = "Forbidden"


def is_in_group(user, group_name, include_superuser=True):
    if include_superuser and user.is_superuser:
        return True
    user_groups = [group.name for group in user.groups.all()]
    return group_name in user_groups


class IsSuperUser(BasePermission):
    """
    Only authenticates superusers.
    """

    message = AUTH_FAILURE_MESSAGE

    def has_permission(self, request, view):
        return request.user.is_superuser


class UserInSmsManagerGroup(BasePermission):
    message = AUTH_FAILURE_MESSAGE

    def has_permission(self, request, view):
        return is_in_group(request.user, "SmsManager")


class UserInSmsWebhookCaller(BasePermission):
    message = AUTH_FAILURE_MESSAGE

    def has_permission(self, request, view):
        return is_in_group(request.user, "SmsWebhookCaller")
