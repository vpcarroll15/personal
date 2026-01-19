from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from food_tracking.constants import (
    DEFAULT_RECENT_CONSUMPTION_LIMIT,
    DEFAULT_REPORT_DAYS,
)
from food_tracking.models import Consumption, Food


def get_active_foods() -> list[Food]:
    """Return all active foods ordered for display."""
    return list(Food.objects.filter(active=True))


def calculate_totals_by_period(
    user_id: int, days: int, period: str
) -> list[dict[str, str | Decimal]]:
    """
    Calculate calorie totals grouped by period.

    Args:
        user_id: User ID to filter consumptions
        days: Number of days to look back
        period: Grouping period ('day', 'week', or 'month')

    Returns:
        List of dicts with 'period' and 'total_calories' keys
    """
    start_date = timezone.now() - timedelta(days=days)
    consumptions = Consumption.objects.filter(
        user_id=user_id, consumed_at__gte=start_date
    ).select_related("food")

    # Define period key functions
    def get_day_key(dt: datetime) -> str:
        return dt.strftime("%Y-%m-%d")

    def get_week_key(dt: datetime) -> str:
        year, week, _ = dt.isocalendar()
        return f"{year}-W{week:02d}"

    def get_month_key(dt: datetime) -> str:
        return dt.strftime("%Y-%m")

    period_key_functions = {
        "day": get_day_key,
        "week": get_week_key,
        "month": get_month_key,
    }

    # Get the appropriate key function (default to day)
    get_key = period_key_functions.get(period, get_day_key)

    # Group consumptions by period using defaultdict
    totals: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for consumption in consumptions:
        period_key = get_key(consumption.consumed_at)
        totals[period_key] += consumption.total_calories()

    # Return sorted results
    return [
        {"period": period_key, "total_calories": calories}
        for period_key, calories in sorted(totals.items(), reverse=True)
    ]


@login_required
def home(request: HttpRequest) -> HttpResponse:
    """Display food tracking grid and recent consumption."""
    from collections import Counter

    foods = get_active_foods()
    recent_consumption = Consumption.objects.filter(user=request.user).select_related(
        "food"
    )[:DEFAULT_RECENT_CONSUMPTION_LIMIT]

    # Calculate today's consumption counts per food
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_consumption = Consumption.objects.filter(
        user=request.user, consumed_at__gte=today_start
    ).values_list("food_id", flat=True)
    today_counts = Counter(today_consumption)

    # Add today's count to each food object
    for food in foods:
        food.today_count = today_counts.get(food.id, 0)

    context = {
        "foods": foods,
        "recent_consumption": recent_consumption,
    }
    return render(request, "food_tracking/home.html", context)


@login_required
@require_http_methods(["POST"])
def log_consumption(request: HttpRequest) -> JsonResponse:
    """Log a food consumption via AJAX POST."""
    try:
        food_id = request.POST.get("food_id")
        quantity = request.POST.get("quantity", "1.0")

        if not food_id:
            return JsonResponse(
                {"success": False, "error": "Missing food_id"}, status=400
            )

        food = Food.objects.get(id=food_id)
        consumption = Consumption.objects.create(
            user=request.user,
            food=food,
            quantity=Decimal(quantity),
        )

        return JsonResponse(
            {
                "success": True,
                "consumption": consumption.to_dict_for_api(),
            }
        )
    except Food.DoesNotExist:
        return JsonResponse({"success": False, "error": "Food not found"}, status=404)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
def reports(request: HttpRequest) -> HttpResponse:
    """Display calorie consumption reports."""
    days = int(request.GET.get("days", DEFAULT_REPORT_DAYS))
    period = request.GET.get("period", "day")

    # Validate period
    if period not in ["day", "week", "month"]:
        period = "day"

    # Calculate totals
    totals = calculate_totals_by_period(request.user.id, days, period)

    # Get detailed consumption for the period
    start_date = timezone.now() - timedelta(days=days)
    detailed_consumption = Consumption.objects.filter(
        user=request.user, consumed_at__gte=start_date
    ).select_related("food")

    context = {
        "days": days,
        "period": period,
        "totals": totals,
        "detailed_consumption": detailed_consumption,
    }
    return render(request, "food_tracking/reports.html", context)
