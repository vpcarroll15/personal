from django.contrib.auth.models import User, Group
from rest_framework.test import APITestCase

from daily_goals.models import User as DailyGoalsUser


class AccountTests(APITestCase):
    def setUp(self):
        webhooker = User.objects.create_user(
            "webhooker", "paul@carroll.com", "paulpassword"
        )
        webhook_group, _ = Group.objects.get_or_create(name="DailyGoalsWebhookCaller")
        webhook_group.user_set.add(webhooker)

        manager = User.objects.create_user(
            "manager", "paul2@carroll.com", "paulpassword"
        )
        manager_group, _ = Group.objects.get_or_create(name="DailyGoalsManager")
        manager_group.user_set.add(manager)

        User.objects.create_user("hacker", "hacked@carroll.com", "paulpassword")

        DailyGoalsUser.objects.get_or_create(
            phone_number="+13033033003",
            logged_in_user=webhooker,
            start_text_hour=6,
            end_text_hour=20,
            possible_focus_areas=["health", "productivity"],
        )

    def test_bad_auth(self):
        user = User.objects.get(username="hacker")
        self.client.force_authenticate(user=user)
        response = self.client.get("/daily_goals/users/", {})
        assert response.status_code == 403

    def test_get_users(self):
        user = User.objects.get(username="manager")
        self.client.force_authenticate(user=user)

        response = self.client.get("/daily_goals/users/", {})
        assert response.status_code == 200
        assert "users" in response.data
        assert len(response.data["users"]) == 1
