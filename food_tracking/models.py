from decimal import Decimal
from typing import Any

from django.conf import settings
from django.db import models
from django.utils import timezone

# Constants
DEFAULT_DAILY_CALORIE_TARGET = 2000


class CalorieTarget(models.Model):
    """Stores a user's single fixed daily calorie target."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    daily_calorie_target = models.PositiveIntegerField(
        default=DEFAULT_DAILY_CALORIE_TARGET,
        help_text="Calories the user aims to stay within each day.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user__username"]
        verbose_name = "Calorie Target"
        verbose_name_plural = "Calorie Targets"

    def __str__(self) -> str:
        return f"{self.user.username}: {self.daily_calorie_target} cal/day"

    def to_dict_for_api(self) -> dict[str, Any]:
        """Serialize target for API responses."""
        return {
            "id": self.id,
            "user": self.user.username,
            "daily_calorie_target": self.daily_calorie_target,
        }


class Food(models.Model):
    """Represents a trackable food item with nutritional information."""

    name = models.CharField(max_length=100, unique=True)
    icon = models.CharField(max_length=10, help_text="Unicode emoji")
    serving_size = models.CharField(
        max_length=50, help_text='e.g., "1 oz", "1 dried fig"'
    )
    calories_per_serving = models.DecimalField(max_digits=6, decimal_places=2)
    display_order = models.PositiveIntegerField(
        default=0, help_text="Order in grid display"
    )
    active = models.BooleanField(default=True, help_text="Show in tracking grid")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name = "Food"
        verbose_name_plural = "Foods"

    def __str__(self) -> str:
        return f"{self.icon} {self.name}"

    def to_dict_for_api(self) -> dict[str, str | int | float | bool]:
        """Serialize food for API responses."""
        return {
            "id": self.id,
            "name": self.name,
            "icon": self.icon,
            "serving_size": self.serving_size,
            "calories_per_serving": float(self.calories_per_serving),
            "display_order": self.display_order,
            "active": self.active,
        }


class Consumption(models.Model):
    """Records when a user consumes a food item."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    # Grid entries reference a predefined Food. AI/recipe estimates leave this
    # null and store the description + calories directly on the row instead.
    food = models.ForeignKey(Food, on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.DecimalField(
        max_digits=5, decimal_places=2, default=1.0, help_text="Number of servings"
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        help_text="Free-text food description for ad-hoc (AI/recipe) entries.",
    )
    calories = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Stored calories for ad-hoc entries (no Food reference).",
    )
    consumed_at = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-consumed_at"]
        verbose_name = "Consumption"
        verbose_name_plural = "Consumptions"
        indexes = [
            models.Index(fields=["user", "-consumed_at"]),
        ]

    def display_name(self) -> str:
        """Human-readable name, whether this is a Food or ad-hoc entry."""
        if self.food is not None:
            return self.food.name
        return self.description or "Food"

    def display_icon(self) -> str:
        """Icon for the entry; ad-hoc estimates use a generic icon."""
        if self.food is not None:
            return self.food.icon
        return "🍽️"

    def __str__(self) -> str:
        timestamp = self.consumed_at.strftime("%Y-%m-%d %H:%M")
        return f"{self.user.username} - {self.display_name()} x{self.quantity} ({timestamp})"

    def total_calories(self) -> Decimal:
        """Calculate total calories for this consumption."""
        if self.food is not None:
            return self.food.calories_per_serving * self.quantity
        return self.calories or Decimal("0")

    def to_dict_for_api(self) -> dict[str, Any]:
        """Serialize consumption for API responses."""
        return {
            "id": self.id,
            "user": self.user.username,
            "food": self.display_name(),
            "food_icon": self.display_icon(),
            "quantity": float(self.quantity),
            "consumed_at": self.consumed_at.isoformat(),
            "total_calories": float(self.total_calories()),
            "notes": self.notes,
        }
