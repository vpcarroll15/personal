"""Unit tests for food_tracking app views."""

from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from freezegun import freeze_time

from food_tracking.models import Consumption, Food
from food_tracking.views import calculate_totals_by_period, get_active_foods


class HelperFunctionTests(TestCase):
    """Tests for helper functions in views.py."""

    @classmethod
    def setUpTestData(cls):
        """Create test data once for the entire test class."""
        cls.user = User.objects.create_user(username="testuser", password="testpass")
        cls.food1 = Food.objects.create(
            name="Test Food H",
            icon="🌰",
            serving_size="1 oz",
            calories_per_serving=Decimal("196.00"),
            display_order=1,
            active=True,
        )
        cls.food2 = Food.objects.create(
            name="Test Food I",
            icon="🥜",
            serving_size="1 oz",
            calories_per_serving=Decimal("157.00"),
            display_order=2,
            active=False,
        )

    def test_get_active_foods_returns_only_active(self):
        """Test that get_active_foods returns only active foods."""
        foods = [f for f in get_active_foods() if f.name.startswith("Test")]
        self.assertEqual(len(foods), 1)
        self.assertEqual(foods[0].name, "Test Food H")

    def test_get_active_foods_ordering(self):
        """Test that get_active_foods returns foods in correct order."""
        food3 = Food.objects.create(
            name="Test Food G",
            icon="🌰",
            serving_size="1 oz",
            calories_per_serving=Decimal("164.00"),
            display_order=0,
            active=True,
        )
        foods = [f for f in get_active_foods() if f.name.startswith("Test")]
        self.assertEqual(len(foods), 2)
        self.assertEqual(foods[0].name, "Test Food G")
        self.assertEqual(foods[1].name, "Test Food H")

    @freeze_time("2024-01-15 12:00:00")
    def test_calculate_totals_by_period_day(self):
        """Test calculate_totals_by_period with day grouping."""
        # Create consumptions on different days
        with freeze_time("2024-01-14 10:00:00"):
            Consumption.objects.create(
                user=self.user, food=self.food1, quantity=Decimal("1.0")
            )
        with freeze_time("2024-01-14 15:00:00"):
            Consumption.objects.create(
                user=self.user, food=self.food1, quantity=Decimal("2.0")
            )
        with freeze_time("2024-01-15 09:00:00"):
            Consumption.objects.create(
                user=self.user, food=self.food1, quantity=Decimal("1.0")
            )

        totals = calculate_totals_by_period(self.user.id, days=7, period="day")

        self.assertEqual(len(totals), 2)
        # Should be ordered by date descending
        self.assertEqual(totals[0]["period"], "2024-01-15")
        self.assertEqual(totals[0]["total_calories"], Decimal("196.00"))
        self.assertEqual(totals[1]["period"], "2024-01-14")
        self.assertEqual(totals[1]["total_calories"], Decimal("588.00"))  # 196 * 3

    @freeze_time("2024-01-15 12:00:00")
    def test_calculate_totals_by_period_week(self):
        """Test calculate_totals_by_period with week grouping."""
        # Create consumptions in different weeks
        with freeze_time("2024-01-08 10:00:00"):  # Week 2
            Consumption.objects.create(
                user=self.user, food=self.food1, quantity=Decimal("1.0")
            )
        with freeze_time("2024-01-15 10:00:00"):  # Week 3
            Consumption.objects.create(
                user=self.user, food=self.food1, quantity=Decimal("2.0")
            )

        totals = calculate_totals_by_period(self.user.id, days=14, period="week")

        self.assertEqual(len(totals), 2)
        # Verify totals are present (exact week numbers may vary)
        total_calories = sum(t["total_calories"] for t in totals)
        self.assertEqual(total_calories, Decimal("588.00"))  # 196 + (196 * 2)

    @freeze_time("2024-01-15 12:00:00")
    def test_calculate_totals_by_period_month(self):
        """Test calculate_totals_by_period with month grouping."""
        # Create consumptions in different months
        with freeze_time("2023-12-20 10:00:00"):
            Consumption.objects.create(
                user=self.user, food=self.food1, quantity=Decimal("1.0")
            )
        with freeze_time("2024-01-10 10:00:00"):
            Consumption.objects.create(
                user=self.user, food=self.food1, quantity=Decimal("2.0")
            )

        totals = calculate_totals_by_period(self.user.id, days=30, period="month")

        self.assertEqual(len(totals), 2)
        self.assertEqual(totals[0]["period"], "2024-01")
        self.assertEqual(totals[0]["total_calories"], Decimal("392.00"))  # 196 * 2
        self.assertEqual(totals[1]["period"], "2023-12")
        self.assertEqual(totals[1]["total_calories"], Decimal("196.00"))

    @freeze_time("2024-01-15 12:00:00")
    def test_calculate_totals_by_period_respects_days(self):
        """Test that calculate_totals_by_period respects the days parameter."""
        # Create consumption 10 days ago
        with freeze_time("2024-01-05 10:00:00"):
            Consumption.objects.create(
                user=self.user, food=self.food1, quantity=Decimal("1.0")
            )
        # Create consumption 3 days ago
        with freeze_time("2024-01-12 10:00:00"):
            Consumption.objects.create(
                user=self.user, food=self.food1, quantity=Decimal("1.0")
            )

        # Should only get consumption from last 7 days
        totals = calculate_totals_by_period(self.user.id, days=7, period="day")
        self.assertEqual(len(totals), 1)
        self.assertEqual(totals[0]["period"], "2024-01-12")


class FoodTrackingViewTests(TestCase):
    """Tests for food_tracking views."""

    @classmethod
    def setUpTestData(cls):
        """Create test data once for the entire test class."""
        cls.user = User.objects.create_user(username="testuser", password="testpass")
        cls.food1 = Food.objects.create(
            name="Test Food H",
            icon="🌰",
            serving_size="1 oz",
            calories_per_serving=Decimal("196.00"),
            display_order=1,
            active=True,
        )
        cls.food2 = Food.objects.create(
            name="Test Food I",
            icon="🥜",
            serving_size="1 oz",
            calories_per_serving=Decimal("157.00"),
            display_order=2,
            active=False,
        )

    def setUp(self):
        """Set up test client and login."""
        self.client = Client()
        self.client.login(username="testuser", password="testpass")

    def test_home_requires_login(self):
        """Test that home view requires login."""
        self.client.logout()
        response = self.client.get(reverse("food_tracking:home"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_home_shows_active_foods(self):
        """Test that home view shows only active foods."""
        response = self.client.get(reverse("food_tracking:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Food H")
        self.assertNotContains(response, "Test Food I")

    def test_home_shows_today_consumption(self):
        """Test that home view shows today's consumption."""
        consumption = Consumption.objects.create(
            user=self.user, food=self.food1, quantity=Decimal("2.0")
        )
        response = self.client.get(reverse("food_tracking:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Food H")
        self.assertContains(response, "2.0")

    @freeze_time("2024-01-15 10:00:00")
    def test_home_shows_only_today_consumption(self):
        """Test that home view shows only today's consumption, not older items."""
        # Create consumption from yesterday
        yesterday = timezone.now() - timezone.timedelta(days=1)
        Consumption.objects.create(
            user=self.user,
            food=self.food1,
            quantity=Decimal("1.0"),
            consumed_at=yesterday,
        )

        # Create consumption from today
        Consumption.objects.create(
            user=self.user, food=self.food2, quantity=Decimal("2.0")
        )

        response = self.client.get(reverse("food_tracking:home"))
        self.assertEqual(response.status_code, 200)
        # Should only show today's consumption (1 item)
        self.assertEqual(len(response.context["today_consumption"]), 1)
        self.assertEqual(response.context["today_consumption"][0].food, self.food2)

    @freeze_time("2024-01-15 07:30:00")
    def test_home_uses_pacific_timezone(self):
        """Test that today's consumption uses Pacific timezone, not UTC."""
        # At 7:30 AM UTC on Jan 15, it's 11:30 PM Pacific on Jan 14
        # "Today" in Pacific time is Jan 14, so this SHOULD be counted
        consumption_at_frozen_time = Consumption.objects.create(
            user=self.user, food=self.food1, quantity=Decimal("1.0")
        )

        response = self.client.get(reverse("food_tracking:home"))
        self.assertEqual(response.status_code, 200)
        # Should show 1 item because "today" is Jan 14 in Pacific time
        self.assertEqual(len(response.context["today_consumption"]), 1)

        # Now create a consumption from Jan 13 (more than 24 hours ago)
        jan_13 = timezone.now() - timezone.timedelta(hours=25)
        Consumption.objects.create(
            user=self.user, food=self.food2, quantity=Decimal("2.0"), consumed_at=jan_13
        )

        response = self.client.get(reverse("food_tracking:home"))
        # Should still only show 1 item (Jan 14), not the Jan 13 one
        self.assertEqual(len(response.context["today_consumption"]), 1)

    @freeze_time("2024-01-15 08:00:00")
    def test_home_pacific_midnight_boundary(self):
        """Test that Pacific midnight (8 AM UTC) is the boundary for 'today'."""
        # At 8:00 AM UTC on Jan 15, it's exactly midnight Pacific on Jan 15
        # This should be counted as "today"
        consumption_at_pacific_midnight = Consumption.objects.create(
            user=self.user, food=self.food1, quantity=Decimal("1.0")
        )

        response = self.client.get(reverse("food_tracking:home"))
        self.assertEqual(response.status_code, 200)
        # Should show 1 item because it's now Jan 15 in Pacific time
        self.assertEqual(len(response.context["today_consumption"]), 1)

    def test_log_consumption_requires_login(self):
        """Test that log_consumption requires login."""
        self.client.logout()
        response = self.client.post(
            reverse("food_tracking:log_consumption"), {"food_id": self.food1.id}
        )
        self.assertEqual(response.status_code, 302)

    def test_log_consumption_rejects_get(self):
        """Test that log_consumption rejects GET requests."""
        response = self.client.get(reverse("food_tracking:log_consumption"))
        self.assertEqual(response.status_code, 405)

    def test_log_consumption_creates_record(self):
        """Test that log_consumption creates a consumption record."""
        response = self.client.post(
            reverse("food_tracking:log_consumption"),
            {"food_id": self.food1.id, "quantity": "2.5"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])

        # Verify consumption was created
        consumption = Consumption.objects.get(user=self.user, food=self.food1)
        self.assertEqual(consumption.quantity, Decimal("2.5"))

    def test_log_consumption_default_quantity(self):
        """Test that log_consumption uses default quantity of 1.0."""
        response = self.client.post(
            reverse("food_tracking:log_consumption"), {"food_id": self.food1.id}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])

        # Verify default quantity
        consumption = Consumption.objects.get(user=self.user, food=self.food1)
        self.assertEqual(consumption.quantity, Decimal("1.0"))

    def test_log_consumption_missing_food_id(self):
        """Test that log_consumption handles missing food_id."""
        response = self.client.post(reverse("food_tracking:log_consumption"), {})
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("Missing food_id", data["error"])

    def test_log_consumption_invalid_food_id(self):
        """Test that log_consumption handles invalid food_id."""
        response = self.client.post(
            reverse("food_tracking:log_consumption"), {"food_id": 99999}
        )
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("Food not found", data["error"])

    @patch("food_tracking.views.Consumption.objects.create")
    def test_log_consumption_handles_general_exception(self, mock_create):
        """Test that log_consumption handles general exceptions."""
        mock_create.side_effect = ValueError("Test error")
        response = self.client.post(
            reverse("food_tracking:log_consumption"), {"food_id": self.food1.id}
        )
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("Test error", data["error"])

    def test_delete_consumption_requires_login(self):
        """Test that delete_consumption requires login."""
        consumption = Consumption.objects.create(
            user=self.user, food=self.food1, quantity=Decimal("1.0")
        )
        self.client.logout()
        response = self.client.post(
            reverse("food_tracking:delete_consumption"),
            {"consumption_id": consumption.id},
        )
        self.assertEqual(response.status_code, 302)

    def test_delete_consumption_rejects_get(self):
        """Test that delete_consumption rejects GET requests."""
        response = self.client.get(reverse("food_tracking:delete_consumption"))
        self.assertEqual(response.status_code, 405)

    def test_delete_consumption_deletes_record(self):
        """Test that delete_consumption deletes a consumption record."""
        consumption = Consumption.objects.create(
            user=self.user, food=self.food1, quantity=Decimal("1.0")
        )
        response = self.client.post(
            reverse("food_tracking:delete_consumption"),
            {"consumption_id": consumption.id},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])

        # Verify consumption was deleted
        self.assertFalse(Consumption.objects.filter(id=consumption.id).exists())

    def test_delete_consumption_missing_id(self):
        """Test that delete_consumption handles missing consumption_id."""
        response = self.client.post(reverse("food_tracking:delete_consumption"), {})
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("Missing consumption_id", data["error"])

    def test_delete_consumption_invalid_id(self):
        """Test that delete_consumption handles invalid consumption_id."""
        response = self.client.post(
            reverse("food_tracking:delete_consumption"), {"consumption_id": 99999}
        )
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("Consumption not found", data["error"])

    def test_delete_consumption_only_own_records(self):
        """Test that users can only delete their own consumption records."""
        other_user = User.objects.create_user(username="otheruser", password="testpass")
        other_consumption = Consumption.objects.create(
            user=other_user, food=self.food1, quantity=Decimal("1.0")
        )

        # Try to delete another user's consumption
        response = self.client.post(
            reverse("food_tracking:delete_consumption"),
            {"consumption_id": other_consumption.id},
        )
        self.assertEqual(response.status_code, 404)

        # Verify it wasn't deleted
        self.assertTrue(Consumption.objects.filter(id=other_consumption.id).exists())

    def test_reports_requires_login(self):
        """Test that reports view requires login."""
        self.client.logout()
        response = self.client.get(reverse("food_tracking:reports"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_reports_default_parameters(self):
        """Test that reports view uses default parameters."""
        response = self.client.get(reverse("food_tracking:reports"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["days"], 7)
        self.assertEqual(response.context["period"], "day")

    def test_reports_custom_parameters(self):
        """Test that reports view respects custom parameters."""
        response = self.client.get(
            reverse("food_tracking:reports") + "?days=30&period=week"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["days"], 30)
        self.assertEqual(response.context["period"], "week")

    def test_reports_invalid_period(self):
        """Test that reports view validates period parameter."""
        response = self.client.get(reverse("food_tracking:reports") + "?period=invalid")
        self.assertEqual(response.status_code, 200)
        # Should fall back to default
        self.assertEqual(response.context["period"], "day")

    @freeze_time("2024-01-15 12:00:00")
    def test_reports_shows_totals(self):
        """Test that reports view calculates and shows totals."""
        # Create some consumptions
        with freeze_time("2024-01-14 10:00:00"):
            Consumption.objects.create(
                user=self.user, food=self.food1, quantity=Decimal("1.0")
            )
        with freeze_time("2024-01-15 10:00:00"):
            Consumption.objects.create(
                user=self.user, food=self.food1, quantity=Decimal("2.0")
            )

        response = self.client.get(reverse("food_tracking:reports") + "?days=7")
        self.assertEqual(response.status_code, 200)

        totals = response.context["totals"]
        self.assertEqual(len(totals), 2)

    @freeze_time("2024-01-15 12:00:00")
    def test_reports_shows_detailed_consumption(self):
        """Test that reports view shows detailed consumption."""
        consumption = Consumption.objects.create(
            user=self.user, food=self.food1, quantity=Decimal("2.0")
        )

        response = self.client.get(reverse("food_tracking:reports") + "?days=7")
        self.assertEqual(response.status_code, 200)

        detailed = response.context["detailed_consumption"]
        self.assertEqual(len(detailed), 1)
        self.assertEqual(detailed[0].id, consumption.id)

    def test_reports_filters_by_user(self):
        """Test that reports view only shows current user's data."""
        other_user = User.objects.create_user(username="otheruser", password="testpass")
        # Create consumption for other user
        Consumption.objects.create(
            user=other_user, food=self.food1, quantity=Decimal("5.0")
        )
        # Create consumption for current user
        Consumption.objects.create(
            user=self.user, food=self.food1, quantity=Decimal("1.0")
        )

        response = self.client.get(reverse("food_tracking:reports"))
        self.assertEqual(response.status_code, 200)

        detailed = response.context["detailed_consumption"]
        self.assertEqual(len(detailed), 1)
        self.assertEqual(detailed[0].user, self.user)
