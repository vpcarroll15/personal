"""Unit tests for food_tracking app models."""

from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone
from freezegun import freeze_time

from food_tracking.models import CalorieTarget, Consumption, DailyActiveCalories, Food


class FoodModelTests(TestCase):
    """Tests for the Food model."""

    @classmethod
    def setUpTestData(cls):
        """Create test data once for the entire test class."""
        cls.food = Food.objects.create(
            name="Test Food A",
            icon="🌰",
            serving_size="1 oz",
            calories_per_serving=Decimal("196.00"),
            display_order=1,
            active=True,
        )

    def test_food_str(self):
        """Test Food __str__ method."""
        expected = "🌰 Test Food A"
        self.assertEqual(str(self.food), expected)

    def test_food_to_dict_for_api(self):
        """Test Food to_dict_for_api method."""
        result = self.food.to_dict_for_api()

        self.assertEqual(result["name"], "Test Food A")
        self.assertEqual(result["icon"], "🌰")
        self.assertEqual(result["serving_size"], "1 oz")
        self.assertEqual(result["calories_per_serving"], 196.0)
        self.assertEqual(result["display_order"], 1)
        self.assertTrue(result["active"])

    def test_food_ordering(self):
        """Test that foods are ordered by display_order and name."""
        food2 = Food.objects.create(
            name="Test Food C",
            icon="🥜",
            serving_size="1 oz",
            calories_per_serving=Decimal("157.00"),
            display_order=2,
            active=True,
        )
        food3 = Food.objects.create(
            name="Test Food B",
            icon="🌰",
            serving_size="1 oz",
            calories_per_serving=Decimal("164.00"),
            display_order=1,
            active=True,
        )

        foods = list(Food.objects.filter(name__startswith="Test"))
        # Should be ordered by display_order (1, 1, 2), then name (Test Food A, Test Food B, Test Food C)
        self.assertEqual(foods[0], self.food)  # Test Food A (display_order=1)
        self.assertEqual(foods[1], food3)  # Test Food B (display_order=1)
        self.assertEqual(foods[2], food2)  # Test Food C (display_order=2)


class ConsumptionModelTests(TestCase):
    """Tests for the Consumption model."""

    @classmethod
    def setUpTestData(cls):
        """Create test data once for the entire test class."""
        cls.user = User.objects.create_user(username="testuser", password="testpass")
        cls.food = Food.objects.create(
            name="Test Food D",
            icon="🥜",
            serving_size="1 oz",
            calories_per_serving=Decimal("161.00"),
            display_order=1,
            active=True,
        )

    @freeze_time("2024-01-15 10:30:00")
    def test_consumption_str(self):
        """Test Consumption __str__ method."""
        consumption = Consumption.objects.create(
            user=self.user,
            food=self.food,
            quantity=Decimal("2.0"),
        )
        expected = "testuser - Test Food D x2.0 (2024-01-15 10:30)"
        self.assertEqual(str(consumption), expected)

    def test_consumption_total_calories(self):
        """Test Consumption total_calories method."""
        consumption = Consumption.objects.create(
            user=self.user,
            food=self.food,
            quantity=Decimal("2.5"),
        )
        expected = Decimal("161.00") * Decimal("2.5")
        self.assertEqual(consumption.total_calories(), expected)

    def test_consumption_total_calories_single_serving(self):
        """Test Consumption total_calories with single serving."""
        consumption = Consumption.objects.create(
            user=self.user,
            food=self.food,
            quantity=Decimal("1.0"),
        )
        self.assertEqual(consumption.total_calories(), Decimal("161.00"))

    def test_consumption_to_dict_for_api(self):
        """Test Consumption to_dict_for_api method."""
        consumption = Consumption.objects.create(
            user=self.user,
            food=self.food,
            quantity=Decimal("1.5"),
            notes="Test notes",
        )
        result = consumption.to_dict_for_api()

        self.assertEqual(result["user"], "testuser")
        self.assertEqual(result["food"], "Test Food D")
        self.assertEqual(result["food_icon"], "🥜")
        self.assertEqual(result["quantity"], 1.5)
        self.assertEqual(result["total_calories"], 241.5)
        self.assertEqual(result["notes"], "Test notes")
        self.assertIn("consumed_at", result)

    def test_consumption_ordering(self):
        """Test that consumptions are ordered by consumed_at descending."""
        with freeze_time("2024-01-15 10:00:00"):
            consumption1 = Consumption.objects.create(
                user=self.user, food=self.food, quantity=Decimal("1.0")
            )
        with freeze_time("2024-01-15 11:00:00"):
            consumption2 = Consumption.objects.create(
                user=self.user, food=self.food, quantity=Decimal("1.0")
            )
        with freeze_time("2024-01-15 09:00:00"):
            consumption3 = Consumption.objects.create(
                user=self.user, food=self.food, quantity=Decimal("1.0")
            )

        consumptions = list(Consumption.objects.all())
        # Should be ordered by consumed_at descending (latest first)
        self.assertEqual(consumptions[0], consumption2)
        self.assertEqual(consumptions[1], consumption1)
        self.assertEqual(consumptions[2], consumption3)

    def test_consumption_default_quantity(self):
        """Test that Consumption has default quantity of 1.0."""
        consumption = Consumption.objects.create(
            user=self.user,
            food=self.food,
        )
        self.assertEqual(consumption.quantity, Decimal("1.0"))

    def test_consumption_with_notes(self):
        """Test Consumption with notes field."""
        consumption = Consumption.objects.create(
            user=self.user,
            food=self.food,
            quantity=Decimal("1.0"),
            notes="Evening snack",
        )
        self.assertEqual(consumption.notes, "Evening snack")

    def test_consumption_blank_notes(self):
        """Test Consumption with blank notes."""
        consumption = Consumption.objects.create(
            user=self.user,
            food=self.food,
            quantity=Decimal("1.0"),
        )
        self.assertEqual(consumption.notes, "")


class CalorieTargetModelTests(TestCase):
    """Tests for the CalorieTarget model."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="targetuser", password="x")
        cls.target = CalorieTarget.objects.create(
            user=cls.user, daily_calorie_target=1800
        )

    def test_str(self):
        self.assertEqual(str(self.target), "targetuser: 1800 cal/day")

    def test_default_target(self):
        other = User.objects.create_user(username="defaultuser", password="x")
        target = CalorieTarget.objects.create(user=other)
        self.assertEqual(target.daily_calorie_target, 2000)

    def test_to_dict_for_api(self):
        data = self.target.to_dict_for_api()
        self.assertEqual(data["user"], "targetuser")
        self.assertEqual(data["daily_calorie_target"], 1800)


class DailyActiveCaloriesModelTests(TestCase):
    """Tests for the DailyActiveCalories model."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="activeuser", password="x")
        cls.entry = DailyActiveCalories.objects.create(
            user=cls.user, date=date(2026, 6, 20), active_calories=520
        )

    def test_str(self):
        self.assertEqual(str(self.entry), "activeuser: 520 active cal on 2026-06-20")

    def test_to_dict_for_api(self):
        data = self.entry.to_dict_for_api()
        self.assertEqual(data["user"], "activeuser")
        self.assertEqual(data["date"], "2026-06-20")
        self.assertEqual(data["active_calories"], 520)

    def test_unique_per_user_per_day(self):
        with self.assertRaises(IntegrityError):
            DailyActiveCalories.objects.create(
                user=self.user, date=date(2026, 6, 20), active_calories=600
            )


class AdHocConsumptionModelTests(TestCase):
    """Tests for AI/recipe (food-less) Consumption entries."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="adhocuser", password="x")
        cls.food = Food.objects.create(
            name="Test Pecans",
            icon="🌰",
            serving_size="1 oz",
            calories_per_serving=Decimal("189.00"),
            display_order=1,
            active=True,
        )

    def test_ad_hoc_total_calories_uses_stored_value(self):
        consumption = Consumption.objects.create(
            user=self.user,
            food=None,
            description="Burrito bowl",
            calories=Decimal("650.00"),
        )
        self.assertEqual(consumption.total_calories(), Decimal("650.00"))

    def test_ad_hoc_total_calories_defaults_to_zero(self):
        consumption = Consumption.objects.create(
            user=self.user, food=None, description="Mystery"
        )
        self.assertEqual(consumption.total_calories(), Decimal("0"))

    def test_ad_hoc_display_name_and_icon(self):
        consumption = Consumption.objects.create(
            user=self.user, food=None, description="Pad thai", calories=Decimal("700")
        )
        self.assertEqual(consumption.display_name(), "Pad thai")
        self.assertEqual(consumption.display_icon(), "🍽️")

    def test_food_display_name_and_icon(self):
        consumption = Consumption.objects.create(
            user=self.user, food=self.food, quantity=Decimal("1.0")
        )
        self.assertEqual(consumption.display_name(), "Test Pecans")
        self.assertEqual(consumption.display_icon(), "🌰")

    def test_ad_hoc_to_dict_for_api(self):
        consumption = Consumption.objects.create(
            user=self.user,
            food=None,
            description="Sushi",
            calories=Decimal("500.00"),
        )
        data = consumption.to_dict_for_api()
        self.assertEqual(data["food"], "Sushi")
        self.assertEqual(data["food_icon"], "🍽️")
        self.assertEqual(data["total_calories"], 500.0)

    def test_ad_hoc_str_without_food(self):
        consumption = Consumption.objects.create(
            user=self.user, food=None, description="Tacos", calories=Decimal("400")
        )
        self.assertIn("Tacos", str(consumption))


class ExerciseConsumptionModelTests(TestCase):
    """Tests for negative-calorie (exercise) consumptions."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="exmodeluser", password="x")

    def test_negative_consumption_uses_fire_icon(self):
        consumption = Consumption.objects.create(
            user=self.user,
            food=None,
            description="30 min run",
            calories=Decimal("-300"),
        )
        self.assertEqual(consumption.display_icon(), "🔥")
        self.assertEqual(consumption.display_name(), "30 min run")
        self.assertEqual(consumption.total_calories(), Decimal("-300"))
