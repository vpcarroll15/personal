"""Unit tests for food_tracking app admin."""

from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from food_tracking.admin import ConsumptionAdmin
from food_tracking.models import Consumption, Food


class ConsumptionAdminTests(TestCase):
    """Tests for ConsumptionAdmin."""

    @classmethod
    def setUpTestData(cls):
        """Create test data once for the entire test class."""
        cls.user = User.objects.create_user(username="testuser", password="testpass")
        cls.food = Food.objects.create(
            name="Test Food",
            icon="🥜",
            serving_size="1 oz",
            calories_per_serving=Decimal("100.00"),
            display_order=1,
            active=True,
        )
        cls.consumption = Consumption.objects.create(
            user=cls.user,
            food=cls.food,
            quantity=Decimal("2.5"),
        )

    def test_total_calories_display(self):
        """Test that total_calories method returns formatted string."""
        admin = ConsumptionAdmin(Consumption, None)
        result = admin.total_calories(self.consumption)
        self.assertEqual(result, "250.00")
