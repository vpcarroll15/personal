from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


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
    food = models.ForeignKey(Food, on_delete=models.CASCADE)
    quantity = models.DecimalField(
        max_digits=5, decimal_places=2, default=1.0, help_text="Number of servings"
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

    def __str__(self) -> str:
        return f"{self.user.username} - {self.food.name} x{self.quantity} ({self.consumed_at.strftime('%Y-%m-%d %H:%M')})"

    def total_calories(self) -> Decimal:
        """Calculate total calories for this consumption."""
        return self.food.calories_per_serving * self.quantity

    def to_dict_for_api(self) -> dict[str, str | int | float]:
        """Serialize consumption for API responses."""
        return {
            "id": self.id,
            "user": self.user.username,
            "food": self.food.name,
            "food_icon": self.food.icon,
            "quantity": float(self.quantity),
            "consumed_at": self.consumed_at.isoformat(),
            "total_calories": float(self.total_calories()),
            "notes": self.notes,
        }
