"""Unit tests for food_tracking app views."""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from freezegun import freeze_time

from food_tracking.estimation import EstimateResult
from food_tracking.models import CalorieTarget, Consumption, DailyActiveCalories, Food
from food_tracking.views import (
    calculate_totals_by_period,
    get_active_calories_for_date,
    get_active_foods,
    get_pacific_day_bounds,
)


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


class EstimateViewTests(TestCase):
    """Tests for the AI estimate, recipe, log-estimate, and target views."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="estuser", password="testpass")

    def setUp(self):
        self.client = Client()
        self.client.login(username="estuser", password="testpass")

    def test_estimate_requires_login(self):
        self.client.logout()
        response = self.client.post(reverse("food_tracking:estimate"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_estimate_requires_post(self):
        response = self.client.get(reverse("food_tracking:estimate"))
        self.assertEqual(response.status_code, 405)

    @patch("food_tracking.views.estimation.estimate_from_text")
    def test_estimate_from_text_success(self, mock_estimate):
        mock_estimate.return_value = EstimateResult(
            description="Apple", calories=95, confidence="high", items=[]
        )
        response = self.client.post(
            reverse("food_tracking:estimate"), {"text": "one apple"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["estimate"]["calories"], 95)
        mock_estimate.assert_called_once_with("one apple")

    @patch("food_tracking.views.estimation.estimate_from_image")
    def test_estimate_from_image_success(self, mock_estimate):
        mock_estimate.return_value = EstimateResult(
            description="Pizza", calories=400, confidence="medium", items=[]
        )
        upload = SimpleUploadedFile("meal.jpg", b"fakebytes", content_type="image/jpeg")
        response = self.client.post(
            reverse("food_tracking:estimate"), {"image": upload, "note": "big slice"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        args, _ = mock_estimate.call_args
        self.assertEqual(args[1], "image/jpeg")
        self.assertEqual(args[2], "big slice")

    def test_estimate_without_input_returns_400(self):
        response = self.client.post(reverse("food_tracking:estimate"))
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])

    @patch("food_tracking.views.estimation.estimate_from_text")
    def test_estimate_value_error_returns_400(self, mock_estimate):
        mock_estimate.side_effect = ValueError("bad")
        response = self.client.post(
            reverse("food_tracking:estimate"), {"text": "weird"}
        )
        self.assertEqual(response.status_code, 400)

    @patch("food_tracking.views.estimation.estimate_recipe")
    def test_estimate_recipe_success(self, mock_estimate):
        mock_estimate.return_value = EstimateResult(
            description="Lasagna portion", calories=500, confidence="medium", items=[]
        )
        response = self.client.post(
            reverse("food_tracking:estimate_recipe"),
            {"recipe_text": "big recipe", "fraction": "0.25"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        mock_estimate.assert_called_once_with("big recipe", 0.25)

    def test_estimate_recipe_missing_text_returns_400(self):
        response = self.client.post(
            reverse("food_tracking:estimate_recipe"), {"fraction": "0.5"}
        )
        self.assertEqual(response.status_code, 400)

    def test_estimate_recipe_invalid_fraction_returns_400(self):
        response = self.client.post(
            reverse("food_tracking:estimate_recipe"),
            {"recipe_text": "x", "fraction": "abc"},
        )
        self.assertEqual(response.status_code, 400)

    def test_estimate_recipe_out_of_range_fraction_returns_400(self):
        response = self.client.post(
            reverse("food_tracking:estimate_recipe"),
            {"recipe_text": "x", "fraction": "2"},
        )
        self.assertEqual(response.status_code, 400)

    def test_log_estimate_creates_ad_hoc_consumption(self):
        response = self.client.post(
            reverse("food_tracking:log_estimate"),
            {"description": "Burrito", "calories": "650"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        consumption = Consumption.objects.get(user=self.user, description="Burrito")
        self.assertIsNone(consumption.food)
        self.assertEqual(consumption.calories, Decimal("650"))
        self.assertEqual(consumption.total_calories(), Decimal("650"))

    def test_log_estimate_missing_description_returns_400(self):
        response = self.client.post(
            reverse("food_tracking:log_estimate"), {"calories": "100"}
        )
        self.assertEqual(response.status_code, 400)

    def test_log_estimate_invalid_calories_returns_400(self):
        response = self.client.post(
            reverse("food_tracking:log_estimate"),
            {"description": "x", "calories": "abc"},
        )
        self.assertEqual(response.status_code, 400)

    def test_log_estimate_negative_calories_returns_400(self):
        response = self.client.post(
            reverse("food_tracking:log_estimate"),
            {"description": "x", "calories": "-5"},
        )
        self.assertEqual(response.status_code, 400)

    def test_set_target_creates_target(self):
        response = self.client.post(
            reverse("food_tracking:set_target"), {"daily_calorie_target": "1800"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        target = CalorieTarget.objects.get(user=self.user)
        self.assertEqual(target.daily_calorie_target, 1800)

    def test_set_target_updates_existing(self):
        CalorieTarget.objects.create(user=self.user, daily_calorie_target=2000)
        self.client.post(
            reverse("food_tracking:set_target"), {"daily_calorie_target": "2500"}
        )
        target = CalorieTarget.objects.get(user=self.user)
        self.assertEqual(target.daily_calorie_target, 2500)

    def test_set_target_invalid_returns_400(self):
        response = self.client.post(
            reverse("food_tracking:set_target"), {"daily_calorie_target": "abc"}
        )
        self.assertEqual(response.status_code, 400)

    def test_set_target_non_positive_returns_400(self):
        response = self.client.post(
            reverse("food_tracking:set_target"), {"daily_calorie_target": "0"}
        )
        self.assertEqual(response.status_code, 400)

    def test_home_includes_target_and_remaining(self):
        CalorieTarget.objects.create(
            user=self.user, daily_calorie_target=2000, goal_deficit=0
        )
        Consumption.objects.create(
            user=self.user, food=None, description="Snack", calories=Decimal("300")
        )
        response = self.client.get(reverse("food_tracking:home"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["base_rate"], 2000)
        # No active-calories history: budget = 2000 base + 500 default estimate
        # - 0 deficit. remaining = 2500 - 300 = 2200.
        self.assertEqual(response.context["remaining_calories"], Decimal("2200"))

    def test_home_creates_default_target(self):
        response = self.client.get(reverse("food_tracking:home"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(CalorieTarget.objects.filter(user=self.user).exists())


class EstimateViewErrorPathTests(TestCase):
    """Tests for the defensive 500 handlers on the new views."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="erruser", password="testpass")

    def setUp(self):
        self.client = Client()
        self.client.login(username="erruser", password="testpass")

    @patch("food_tracking.views.estimation.estimate_from_text")
    def test_estimate_unexpected_error_returns_500(self, mock_estimate):
        mock_estimate.side_effect = RuntimeError("boom")
        response = self.client.post(reverse("food_tracking:estimate"), {"text": "food"})
        self.assertEqual(response.status_code, 500)

    @patch("food_tracking.views.estimation.estimate_recipe")
    def test_estimate_recipe_unexpected_error_returns_500(self, mock_estimate):
        mock_estimate.side_effect = RuntimeError("boom")
        response = self.client.post(
            reverse("food_tracking:estimate_recipe"),
            {"recipe_text": "r", "fraction": "0.5"},
        )
        self.assertEqual(response.status_code, 500)

    @patch("food_tracking.views.estimation.estimate_recipe")
    def test_estimate_recipe_value_error_returns_400(self, mock_estimate):
        mock_estimate.side_effect = ValueError("bad")
        response = self.client.post(
            reverse("food_tracking:estimate_recipe"),
            {"recipe_text": "r", "fraction": "0.5"},
        )
        self.assertEqual(response.status_code, 400)

    @patch("food_tracking.views.Consumption.objects.create")
    def test_log_estimate_unexpected_error_returns_500(self, mock_create):
        mock_create.side_effect = RuntimeError("boom")
        response = self.client.post(
            reverse("food_tracking:log_estimate"),
            {"description": "x", "calories": "100"},
        )
        self.assertEqual(response.status_code, 500)

    @patch("food_tracking.views.CalorieTarget.objects.update_or_create")
    def test_set_target_unexpected_error_returns_500(self, mock_update):
        mock_update.side_effect = RuntimeError("boom")
        response = self.client.post(
            reverse("food_tracking:set_target"), {"daily_calorie_target": "1800"}
        )
        self.assertEqual(response.status_code, 500)


class SetGoalDeficitViewTests(TestCase):
    """Tests for setting the per-user goal deficit."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="defuser", password="testpass")

    def setUp(self):
        self.client = Client()
        self.client.login(username="defuser", password="testpass")

    def test_requires_login(self):
        self.client.logout()
        response = self.client.post(reverse("food_tracking:set_goal_deficit"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_requires_post(self):
        response = self.client.get(reverse("food_tracking:set_goal_deficit"))
        self.assertEqual(response.status_code, 405)

    def test_creates_target_with_deficit(self):
        response = self.client.post(
            reverse("food_tracking:set_goal_deficit"), {"goal_deficit": "750"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertEqual(CalorieTarget.objects.get(user=self.user).goal_deficit, 750)

    def test_updates_existing_deficit(self):
        CalorieTarget.objects.create(
            user=self.user, daily_calorie_target=1800, goal_deficit=500
        )
        self.client.post(
            reverse("food_tracking:set_goal_deficit"), {"goal_deficit": "300"}
        )
        target = CalorieTarget.objects.get(user=self.user)
        self.assertEqual(target.goal_deficit, 300)
        # Base rate is preserved when only the deficit changes.
        self.assertEqual(target.daily_calorie_target, 1800)

    def test_zero_deficit_allowed(self):
        response = self.client.post(
            reverse("food_tracking:set_goal_deficit"), {"goal_deficit": "0"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(CalorieTarget.objects.get(user=self.user).goal_deficit, 0)

    def test_invalid_value_returns_400(self):
        response = self.client.post(
            reverse("food_tracking:set_goal_deficit"), {"goal_deficit": "abc"}
        )
        self.assertEqual(response.status_code, 400)

    def test_negative_value_returns_400(self):
        response = self.client.post(
            reverse("food_tracking:set_goal_deficit"), {"goal_deficit": "-100"}
        )
        self.assertEqual(response.status_code, 400)

    @patch("food_tracking.views.CalorieTarget.objects.update_or_create")
    def test_unexpected_error_returns_500(self, mock_update):
        mock_update.side_effect = RuntimeError("boom")
        response = self.client.post(
            reverse("food_tracking:set_goal_deficit"), {"goal_deficit": "500"}
        )
        self.assertEqual(response.status_code, 500)


class GetActiveCaloriesForDateTests(TestCase):
    """Tests for the active-calories estimation helper."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="acuser", password="testpass")

    def test_logged_day_returns_value_not_estimate(self):
        day = date(2026, 6, 20)
        DailyActiveCalories.objects.create(
            user=self.user, date=day, active_calories=512
        )
        value, is_estimate = get_active_calories_for_date(self.user, day)
        self.assertEqual(value, 512)
        self.assertFalse(is_estimate)

    def test_no_history_returns_default_estimate(self):
        value, is_estimate = get_active_calories_for_date(self.user, date(2026, 6, 20))
        self.assertEqual(value, 500)
        self.assertTrue(is_estimate)

    def test_too_few_logged_days_returns_default_estimate(self):
        day = date(2026, 6, 20)
        # Only two logged days — below the minimum, so fall back to the default.
        for offset, cals in [(1, 900), (3, 1000)]:
            DailyActiveCalories.objects.create(
                user=self.user,
                date=day - timedelta(days=offset),
                active_calories=cals,
            )
        value, is_estimate = get_active_calories_for_date(self.user, day)
        self.assertEqual(value, 500)
        self.assertTrue(is_estimate)

    def test_estimate_averages_logged_days_only(self):
        day = date(2026, 6, 20)
        # Three logged days within the prior 14; unlogged days are ignored.
        for offset, cals in [(1, 480), (3, 520), (5, 620)]:
            DailyActiveCalories.objects.create(
                user=self.user,
                date=day - timedelta(days=offset),
                active_calories=cals,
            )
        value, is_estimate = get_active_calories_for_date(self.user, day)
        # round((480 + 520 + 620) / 3) = 540
        self.assertEqual(value, 540)
        self.assertTrue(is_estimate)

    def test_estimate_excludes_days_outside_window(self):
        day = date(2026, 6, 20)
        # Three logged days in-window (enough to trust the average).
        for offset, cals in [(1, 400), (2, 500), (4, 600)]:
            DailyActiveCalories.objects.create(
                user=self.user,
                date=day - timedelta(days=offset),
                active_calories=cals,
            )
        # Outside the 14-day window — must be excluded from the average.
        DailyActiveCalories.objects.create(
            user=self.user, date=day - timedelta(days=20), active_calories=2000
        )
        value, _ = get_active_calories_for_date(self.user, day)
        # round((400 + 500 + 600) / 3) = 500; the 2000 outside the window is ignored.
        self.assertEqual(value, 500)


class SetActiveCaloriesViewTests(TestCase):
    """Tests for setting today's Apple Watch active calories."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="acuser", password="testpass")

    def setUp(self):
        self.client = Client()
        self.client.login(username="acuser", password="testpass")

    def test_requires_login(self):
        self.client.logout()
        response = self.client.post(reverse("food_tracking:set_active_calories"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_requires_post(self):
        response = self.client.get(reverse("food_tracking:set_active_calories"))
        self.assertEqual(response.status_code, 405)

    def test_creates_entry(self):
        response = self.client.post(
            reverse("food_tracking:set_active_calories"), {"active_calories": "450"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertEqual(DailyActiveCalories.objects.filter(user=self.user).count(), 1)
        self.assertEqual(
            DailyActiveCalories.objects.get(user=self.user).active_calories, 450
        )

    def test_updates_existing_entry(self):
        self.client.post(
            reverse("food_tracking:set_active_calories"), {"active_calories": "450"}
        )
        self.client.post(
            reverse("food_tracking:set_active_calories"), {"active_calories": "600"}
        )
        # Upsert: still one row, updated value.
        self.assertEqual(DailyActiveCalories.objects.filter(user=self.user).count(), 1)
        self.assertEqual(
            DailyActiveCalories.objects.get(user=self.user).active_calories, 600
        )

    def test_invalid_value_returns_400(self):
        response = self.client.post(
            reverse("food_tracking:set_active_calories"), {"active_calories": "abc"}
        )
        self.assertEqual(response.status_code, 400)

    def test_negative_value_returns_400(self):
        response = self.client.post(
            reverse("food_tracking:set_active_calories"), {"active_calories": "-5"}
        )
        self.assertEqual(response.status_code, 400)

    @patch("food_tracking.views.DailyActiveCalories.objects.update_or_create")
    def test_unexpected_error_returns_500(self, mock_upsert):
        mock_upsert.side_effect = RuntimeError("boom")
        response = self.client.post(
            reverse("food_tracking:set_active_calories"), {"active_calories": "450"}
        )
        self.assertEqual(response.status_code, 500)

    def test_active_calories_add_to_budget(self):
        CalorieTarget.objects.create(
            user=self.user, daily_calorie_target=1800, goal_deficit=300
        )
        Consumption.objects.create(
            user=self.user, food=None, description="Lunch", calories=Decimal("800")
        )
        self.client.post(
            reverse("food_tracking:set_active_calories"), {"active_calories": "500"}
        )
        response = self.client.get(reverse("food_tracking:home"))
        # budget = 1800 base + 500 active - 300 deficit = 2000; rem = 2000 - 800
        self.assertEqual(response.context["today_total_calories"], Decimal("800"))
        self.assertEqual(response.context["base_rate"], 1800)
        self.assertEqual(response.context["active_calories"], 500)
        self.assertFalse(response.context["active_is_estimate"])
        self.assertEqual(response.context["goal_deficit"], 300)
        self.assertEqual(response.context["effective_budget"], 2000)
        self.assertEqual(response.context["remaining_calories"], Decimal("1200"))

    def test_home_uses_estimate_when_unlogged(self):
        CalorieTarget.objects.create(
            user=self.user, daily_calorie_target=1800, goal_deficit=500
        )
        response = self.client.get(reverse("food_tracking:home"))
        # No history yet: falls back to the default estimate, flagged as estimate.
        # budget = 1800 base + 500 estimate - 500 deficit = 1800.
        self.assertEqual(response.context["active_calories"], 500)
        self.assertTrue(response.context["active_is_estimate"])
        self.assertEqual(response.context["effective_budget"], 1800)


class PastDayViewTests(TestCase):
    """Tests for viewing and logging against a past day via ?date= / POST date."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="pastday", password="testpass")
        cls.food = Food.objects.create(
            name="Past Day Food",
            icon="🍕",
            serving_size="1 slice",
            calories_per_serving=Decimal("285.00"),
            active=True,
        )

    def setUp(self):
        self.client = Client()
        self.client.login(username="pastday", password="testpass")

    # -- home view -------------------------------------------------------

    @freeze_time("2024-01-15 20:00:00")  # noon Pacific on Jan 15
    def test_home_with_past_date_shows_that_days_consumption(self):
        # Noon Pacific on Jan 14 is 20:00 UTC
        Consumption.objects.create(
            user=self.user,
            food=self.food,
            quantity=Decimal("1.0"),
            consumed_at=timezone.now() - timedelta(days=1),
        )
        Consumption.objects.create(
            user=self.user, food=self.food, quantity=Decimal("2.0")
        )

        response = self.client.get(
            reverse("food_tracking:home"), {"date": "2024-01-14"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["today_consumption"]), 1)
        self.assertEqual(
            response.context["today_consumption"][0].quantity, Decimal("1.0")
        )
        self.assertFalse(response.context["is_today"])
        self.assertEqual(response.context["view_date"], date(2024, 1, 14))
        self.assertEqual(response.context["prev_date"], "2024-01-13")
        self.assertEqual(response.context["next_date"], "2024-01-15")

    @freeze_time("2024-01-15 20:00:00")
    def test_home_default_is_today(self):
        response = self.client.get(reverse("food_tracking:home"))
        self.assertTrue(response.context["is_today"])
        self.assertEqual(response.context["view_date"], date(2024, 1, 15))

    @freeze_time("2024-01-15 20:00:00")
    def test_home_future_date_falls_back_to_today(self):
        response = self.client.get(
            reverse("food_tracking:home"), {"date": "2024-01-16"}
        )
        self.assertTrue(response.context["is_today"])
        self.assertEqual(response.context["view_date"], date(2024, 1, 15))

    @freeze_time("2024-01-15 20:00:00")
    def test_home_malformed_date_falls_back_to_today(self):
        response = self.client.get(
            reverse("food_tracking:home"), {"date": "not-a-date"}
        )
        self.assertTrue(response.context["is_today"])
        self.assertEqual(response.context["view_date"], date(2024, 1, 15))

    @freeze_time("2024-01-15 20:00:00")
    def test_home_past_day_shows_banner(self):
        response = self.client.get(
            reverse("food_tracking:home"), {"date": "2024-01-14"}
        )
        self.assertContains(response, "Viewing a past day")

    @freeze_time("2024-01-15 20:00:00")
    def test_home_past_day_uses_that_days_active_calories(self):
        DailyActiveCalories.objects.create(
            user=self.user, date=date(2024, 1, 14), active_calories=650
        )
        response = self.client.get(
            reverse("food_tracking:home"), {"date": "2024-01-14"}
        )
        self.assertEqual(response.context["active_calories"], 650)
        self.assertFalse(response.context["active_is_estimate"])

    # -- log_consumption -------------------------------------------------

    @freeze_time("2024-01-15 20:00:00")
    def test_log_consumption_backdates_to_noon_pacific(self):
        response = self.client.post(
            reverse("food_tracking:log_consumption"),
            {"food_id": self.food.id, "quantity": "1.0", "date": "2024-01-10"},
        )
        self.assertEqual(response.status_code, 200)

        consumption = Consumption.objects.get(user=self.user)
        consumed_pacific = consumption.consumed_at.astimezone(
            timezone.get_fixed_timezone(-480)  # PST (UTC-8) in January
        )
        self.assertEqual(consumed_pacific.date(), date(2024, 1, 10))
        self.assertEqual(consumed_pacific.hour, 12)

    @freeze_time("2024-01-15 20:00:00")
    def test_log_consumption_today_date_uses_current_time(self):
        response = self.client.post(
            reverse("food_tracking:log_consumption"),
            {"food_id": self.food.id, "quantity": "1.0", "date": "2024-01-15"},
        )
        self.assertEqual(response.status_code, 200)

        consumption = Consumption.objects.get(user=self.user)
        self.assertEqual(consumption.consumed_at, timezone.now())

    @freeze_time("2024-01-15 20:00:00")
    def test_log_consumption_rejects_future_date(self):
        response = self.client.post(
            reverse("food_tracking:log_consumption"),
            {"food_id": self.food.id, "date": "2024-01-16"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid date", response.json()["error"])
        self.assertEqual(Consumption.objects.count(), 0)

    def test_log_consumption_rejects_malformed_date(self):
        response = self.client.post(
            reverse("food_tracking:log_consumption"),
            {"food_id": self.food.id, "date": "yesterday"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Consumption.objects.count(), 0)

    # -- log_estimate ------------------------------------------------------

    @freeze_time("2024-01-15 20:00:00")
    def test_log_estimate_backdates_to_noon_pacific(self):
        response = self.client.post(
            reverse("food_tracking:log_estimate"),
            {"description": "Forgotten pizza", "calories": "600", "date": "2024-01-14"},
        )
        self.assertEqual(response.status_code, 200)

        consumption = Consumption.objects.get(user=self.user)
        consumed_pacific = consumption.consumed_at.astimezone(
            timezone.get_fixed_timezone(-480)
        )
        self.assertEqual(consumed_pacific.date(), date(2024, 1, 14))
        self.assertEqual(consumed_pacific.hour, 12)

    @freeze_time("2024-01-15 20:00:00")
    def test_log_estimate_rejects_future_date(self):
        response = self.client.post(
            reverse("food_tracking:log_estimate"),
            {
                "description": "Time-travel snack",
                "calories": "100",
                "date": "2024-02-01",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Consumption.objects.count(), 0)

    # -- set_active_calories ----------------------------------------------

    @freeze_time("2024-01-15 20:00:00")
    def test_set_active_calories_for_past_day(self):
        response = self.client.post(
            reverse("food_tracking:set_active_calories"),
            {"active_calories": "700", "date": "2024-01-14"},
        )
        self.assertEqual(response.status_code, 200)

        entry = DailyActiveCalories.objects.get(user=self.user)
        self.assertEqual(entry.date, date(2024, 1, 14))
        self.assertEqual(entry.active_calories, 700)
        # Today has no entry
        self.assertFalse(
            DailyActiveCalories.objects.filter(
                user=self.user, date=date(2024, 1, 15)
            ).exists()
        )

    @freeze_time("2024-01-15 20:00:00")
    def test_set_active_calories_rejects_future_date(self):
        response = self.client.post(
            reverse("food_tracking:set_active_calories"),
            {"active_calories": "700", "date": "2024-01-16"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(DailyActiveCalories.objects.count(), 0)


class DayBoundsTests(TestCase):
    """Tests for Pacific day boundary computation, including DST days."""

    def test_normal_day_is_24_hours(self):
        start, end = get_pacific_day_bounds(date(2024, 1, 15))
        self.assertEqual(end - start, timedelta(hours=24))

    def test_spring_forward_day_is_23_hours(self):
        # 2024-03-10: Pacific clocks jump 2am -> 3am
        start, end = get_pacific_day_bounds(date(2024, 3, 10))
        self.assertEqual(end - start, timedelta(hours=23))

    def test_fall_back_day_is_25_hours(self):
        # 2024-11-03: Pacific clocks fall back 2am -> 1am
        start, end = get_pacific_day_bounds(date(2024, 11, 3))
        self.assertEqual(end - start, timedelta(hours=25))
