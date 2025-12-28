from datetime import date

from django.contrib.auth.models import Group, User
from django.test import TestCase
from rest_framework.test import APITestCase

from daily_goals.models import DailyCheckin
from daily_goals.models import User as DailyGoalsUser


class ModelTests(TestCase):
    """Tests for model methods."""

    def test_user_str(self):
        """Test the __str__ method of User."""
        user = User.objects.create_user("testuser", "test@test.com", "password")
        daily_goals_user = DailyGoalsUser.objects.create(
            phone_number="+13033033003",
            logged_in_user=user,
            start_text_hour=6,
            end_text_hour=20,
            possible_focus_areas=["health"],
        )
        self.assertEqual(str(daily_goals_user), "+13033033003")

    def test_daily_checkin_str(self):
        """Test the __str__ method of DailyCheckin."""
        user = User.objects.create_user("testuser", "test@test.com", "password")
        daily_goals_user = DailyGoalsUser.objects.create(
            phone_number="+13033033003",
            logged_in_user=user,
            start_text_hour=6,
            end_text_hour=20,
            possible_focus_areas=["health"],
        )
        checkin = DailyCheckin.objects.create(
            user=daily_goals_user,
            possible_focus_areas=["health", "productivity"],
        )
        result = str(checkin)
        self.assertIn("+13033033003", result)
        self.assertIn(str(checkin.created_at), result)


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
        response = self.client.get("/daily_goals/user/", {})
        assert response.status_code == 403
        response = self.client.post("/daily_goals/checkin/", {})
        assert response.status_code == 403

    def test_get_users(self):
        user = User.objects.get(username="manager")
        self.client.force_authenticate(user=user)

        response = self.client.get("/daily_goals/users/", {})
        assert response.status_code == 200
        assert "users" in response.data
        assert len(response.data["users"]) == 1

    def test_put_user(self):
        user = User.objects.get(username="manager")
        self.client.force_authenticate(user=user)

        daily_goals_user = DailyGoalsUser.objects.get(phone_number="+13033033003")

        response = self.client.put(
            "/daily_goals/user/",
            {
                "id": daily_goals_user.id,
                "last_start_text_sent_date": str(date(year=2023, month=1, day=1)),
                "last_end_text_sent_date": str(date(year=2023, month=1, day=1)),
            },
            format="json",
        )
        assert response.status_code == 200
        assert "user" in response.data
        assert response.data["user"]["last_start_text_sent_date"] == "2023-01-01"
        assert response.data["user"]["last_end_text_sent_date"] == "2023-01-01"

    def test_create_new_user(self):
        """Test creating a new user via PUT with no id."""
        manager = User.objects.get(username="manager")
        self.client.force_authenticate(user=manager)

        # Create a logged_in_user for the daily goals user
        new_logged_in_user = User.objects.create_user(
            "newuser", "new@test.com", "password"
        )

        response = self.client.put(
            "/daily_goals/user/",
            {
                "phone_number": "+15555555555",
                "logged_in_user_id": new_logged_in_user.id,
                "start_text_hour": 8,
                "end_text_hour": 22,
                "possible_focus_areas": ["test"],
            },
            format="json",
        )
        assert response.status_code == 200
        assert "user" in response.data
        assert response.data["user"]["phone_number"] == "+15555555555"
        # Verify it was actually created
        assert DailyGoalsUser.objects.filter(phone_number="+15555555555").exists()

    def test_superuser_can_access(self):
        """Test that a superuser can access even without being in the group."""
        superuser = User.objects.create_superuser(
            "admin", "admin@carroll.com", "adminpassword"
        )
        self.client.force_authenticate(user=superuser)
        response = self.client.get("/daily_goals/users/", {})
        assert response.status_code == 200

    def test_create_checkin(self):
        user = User.objects.get(username="manager")
        self.client.force_authenticate(user=user)

        daily_goals_user = DailyGoalsUser.objects.get(phone_number="+13033033003")
        focus_areas = ["health", "productivity", "happiness"]

        response = self.client.post(
            "/daily_goals/checkin/",
            {"possible_focus_areas": focus_areas, "user_id": daily_goals_user.id},
            format="json",
        )
        assert response.status_code == 201
        assert "checkin" in response.data
        assert response.data["checkin"]["possible_focus_areas"] == focus_areas

        # Also check that we can fetch checkins.
        response = self.client.get(
            "/daily_goals/checkin/",
            {"user_id": daily_goals_user.id, "created_at__gte": "2023-01-01T00:00:00Z"},
        )
        assert response.status_code == 200
        assert len(response.data["checkins"]) == 1
        response = self.client.get(
            "/daily_goals/checkin/",
            {"user_id": 100, "created_at__gte": "2023-01-01T00:00:00Z"},
        )
        assert response.status_code == 200
        assert len(response.data["checkins"]) == 0
        response = self.client.get(
            "/daily_goals/checkin/",
            {"user_id": daily_goals_user.id, "created_at__gte": "3023-01-01T00:00:00Z"},
        )
        assert response.status_code == 200
        assert len(response.data["checkins"]) == 0
        response = self.client.get(
            "/daily_goals/checkin/",
            {"user_id": daily_goals_user.id, "created_at__gte": "notparseable"},
        )
        assert response.status_code == 400

    def test_webhook(self):
        user = User.objects.get(username="webhooker")
        self.client.force_authenticate(user=user)
        # No phone number provided.
        response = self.client.post("/daily_goals/webhook/", {})
        assert response.status_code == 400

        # Garbage phone number provided.
        response = self.client.post(
            "/daily_goals/webhook/", {"From": "+19999999999", "Body": "3"}
        )
        assert response.status_code == 400

        # Good phone number, but there isn't a DataPoint yet in the backend.
        response = self.client.post(
            "/daily_goals/webhook/", {"From": "+13033033003", "Body": "3"}
        )
        assert response.status_code == 400

        daily_goals_user = DailyGoalsUser.objects.get(phone_number="+13033033003")

        # Create a DailyCheckin with already chosen focus areas.
        checkin, _ = DailyCheckin.objects.get_or_create(
            user=daily_goals_user,
            possible_focus_areas=["health", "productivity"],
            chosen_focus_areas=["health", "productivity"],
        )
        response = self.client.post(
            "/daily_goals/webhook/", {"From": "+13033033003", "Body": "3"}
        )
        assert response.status_code == 204

        checkin.chosen_focus_areas = None
        checkin.save()

        # Now let's pass in some messages that can't be parsed.
        response = self.client.post(
            "/daily_goals/webhook/", {"From": "+13033033003", "Body": ""}
        )
        assert response.status_code == 204
        response = self.client.post(
            "/daily_goals/webhook/", {"From": "+13033033003", "Body": "-1"}
        )
        assert response.status_code == 204
        response = self.client.post(
            "/daily_goals/webhook/", {"From": "+13033033003", "Body": "3"}
        )

        # Finally we post a good message!
        response = self.client.post(
            "/daily_goals/webhook/",
            {"From": "+13033033003", "Body": "g 2; 1; happiness"},
        )
        assert response.status_code == 200
        # Reload from DB.
        checkin = DailyCheckin.objects.get(id=checkin.id)
        assert checkin.chosen_focus_areas == ["productivity", "health", "happiness"]

        # Handle duplicates in a somewhat sane way.
        checkin.chosen_focus_areas = None
        checkin.save()
        response = self.client.post(
            "/daily_goals/webhook/",
            {"From": "+13033033003", "Body": "g 2; 1; 2; happiness"},
        )
        assert response.status_code == 200
        # Reload from DB.
        checkin = DailyCheckin.objects.get(id=checkin.id)
        assert checkin.chosen_focus_areas == ["productivity", "health", "happiness"]
