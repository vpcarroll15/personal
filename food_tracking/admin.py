from django.contrib import admin

from food_tracking.models import Consumption, Food


@admin.register(Food)
class FoodAdmin(admin.ModelAdmin):
    list_display = [
        "icon",
        "name",
        "serving_size",
        "calories_per_serving",
        "display_order",
        "active",
    ]
    list_editable = ["display_order", "active"]
    ordering = ["display_order", "name"]
    search_fields = ["name"]


@admin.register(Consumption)
class ConsumptionAdmin(admin.ModelAdmin):
    list_display = ["user", "food", "quantity", "consumed_at", "total_calories"]
    list_filter = ["user", "food", "consumed_at"]
    search_fields = ["user__username", "food__name", "notes"]
    date_hierarchy = "consumed_at"
    readonly_fields = ["total_calories"]

    def total_calories(self, obj: Consumption) -> str:
        """Display total calories for admin list."""
        return f"{obj.total_calories():.2f}"

    total_calories.short_description = "Total Calories"  # type: ignore
