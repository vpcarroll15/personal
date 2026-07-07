import json
from collections import defaultdict
from datetime import date as date_cls
from datetime import datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

import pytz
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Avg, Count
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from food_tracking import estimation
from food_tracking.constants import (
    ACTIVE_CALORIES_WINDOW_DAYS,
    DEFAULT_ACTIVE_CALORIES_ESTIMATE,
    DEFAULT_RECENT_CONSUMPTION_LIMIT,
    DEFAULT_REPORT_DAYS,
    MIN_LOGGED_DAYS_FOR_ESTIMATE,
)
from food_tracking.models import CalorieTarget, Consumption, DailyActiveCalories, Food

# Use Pacific timezone for all date calculations
PACIFIC_TZ = pytz.timezone("America/Los_Angeles")

# Backdated entries (logged against a past day) get this hour, Pacific time.
# Noon sits safely inside the day regardless of DST or UTC conversion, unlike
# midnight which lands exactly on the day boundary.
BACKDATE_HOUR = 12

DATE_PARAM_FORMAT = "%Y-%m-%d"


def get_pacific_today_start() -> datetime:
    """Get the start of today (midnight) in Pacific timezone."""
    now_pacific = timezone.now().astimezone(PACIFIC_TZ)
    today_start_pacific = now_pacific.replace(hour=0, minute=0, second=0, microsecond=0)
    return today_start_pacific


def get_pacific_day_bounds(day: date_cls) -> tuple[datetime, datetime]:
    """Return the [start, end) datetimes of a Pacific calendar day.

    Both bounds are localized midnights rather than start + 24h, so days that
    contain a DST transition (23 or 25 hours long) keep correct boundaries.
    """
    start = PACIFIC_TZ.localize(datetime.combine(day, time.min))
    end = PACIFIC_TZ.localize(datetime.combine(day + timedelta(days=1), time.min))
    return start, end


def get_requested_day(request: HttpRequest) -> date_cls:
    """Return the Pacific day a write request applies to (default: today).

    Raises ValueError for malformed dates or dates in the future, so callers
    can turn either into a 400.
    """
    raw = request.POST.get("date", "").strip()
    today = get_pacific_today_start().date()
    if not raw:
        return today
    day = datetime.strptime(raw, DATE_PARAM_FORMAT).date()
    if day > today:
        raise ValueError("Date cannot be in the future.")
    return day


def resolve_consumed_at(day: date_cls) -> datetime:
    """Timestamp to store for a consumption logged against `day`.

    Entries for today keep the real time so ordering within the day is
    preserved; backdated entries get noon Pacific on that day.
    """
    if day == get_pacific_today_start().date():
        return timezone.now()
    return PACIFIC_TZ.localize(datetime.combine(day, time(hour=BACKDATE_HOUR)))


def get_active_foods() -> list[Food]:
    """Return all active foods ordered for display."""
    return list(Food.objects.filter(active=True))


def get_active_calories_for_date(user: User, day: date_cls) -> tuple[int, bool]:
    """Return the user's active (Move ring) calories for a day.

    If the day has a logged entry, return it. Otherwise estimate from the
    average of logged days in the prior ACTIVE_CALORIES_WINDOW_DAYS (logged days
    only — unlogged days are ignored rather than counted as zero). Until there
    are at least MIN_LOGGED_DAYS_FOR_ESTIMATE logged days the sample is too thin
    to trust, so we fall back to DEFAULT_ACTIVE_CALORIES_ESTIMATE.

    Returns a (value, is_estimate) tuple.
    """
    logged = DailyActiveCalories.objects.filter(user=user, date=day).first()
    if logged is not None:
        return logged.active_calories, False

    window_start = day - timedelta(days=ACTIVE_CALORIES_WINDOW_DAYS)
    stats = DailyActiveCalories.objects.filter(
        user=user, date__gte=window_start, date__lt=day
    ).aggregate(avg=Avg("active_calories"), n=Count("id"))

    if stats["n"] < MIN_LOGGED_DAYS_FOR_ESTIMATE:
        return DEFAULT_ACTIVE_CALORIES_ESTIMATE, True
    return round(stats["avg"]), True


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

    # Define period key functions (convert to Pacific time first)
    def get_day_key(dt: datetime) -> str:
        dt_pacific = dt.astimezone(PACIFIC_TZ)
        return dt_pacific.strftime("%Y-%m-%d")

    def get_week_key(dt: datetime) -> str:
        dt_pacific = dt.astimezone(PACIFIC_TZ)
        year, week, _ = dt_pacific.isocalendar()
        return f"{year}-W{week:02d}"

    def get_month_key(dt: datetime) -> str:
        dt_pacific = dt.astimezone(PACIFIC_TZ)
        return dt_pacific.strftime("%Y-%m")

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
    """Display the food tracking grid and consumption for one Pacific day.

    Defaults to today; ?date=YYYY-MM-DD shows a past day so forgotten entries
    can be logged retroactively. Malformed or future dates fall back to today
    rather than erroring, since they only arrive via hand-edited URLs.
    """
    foods = get_active_foods()

    today = get_pacific_today_start().date()
    try:
        view_date = datetime.strptime(
            request.GET.get("date", ""), DATE_PARAM_FORMAT
        ).date()
    except ValueError:
        view_date = today
    view_date = min(view_date, today)
    is_today = view_date == today

    # All consumption for the viewed day (Pacific), most recent first. The
    # "today_*" names are kept for template compatibility; they mean "the
    # viewed day" throughout.
    day_start, day_end = get_pacific_day_bounds(view_date)
    today_consumption = (
        Consumption.objects.filter(
            user=request.user, consumed_at__gte=day_start, consumed_at__lt=day_end
        )
        .select_related("food")
        .order_by("-consumed_at")
    )

    # Calculate the day's total quantity per food for badges
    today_quantities: dict[int, Decimal] = {}
    for consumption in today_consumption:
        food_id = consumption.food_id
        today_quantities[food_id] = (
            today_quantities.get(food_id, Decimal("0")) + consumption.quantity
        )

    # Add the day's total quantity to each food object
    for food in foods:
        food.today_count = today_quantities.get(food.id, Decimal("0"))

    # Calculate total calories consumed on the viewed day (food only)
    today_total_calories = sum(c.total_calories() for c in today_consumption)

    target = get_or_create_target(request.user)
    base_rate = target.daily_calorie_target
    goal_deficit = target.goal_deficit

    # Active calories (Apple Watch Move ring) layered on top of the base rate,
    # less the goal deficit the user is aiming for.
    active_calories, active_is_estimate = get_active_calories_for_date(
        request.user, view_date
    )
    effective_budget = base_rate + active_calories - goal_deficit
    remaining_calories = effective_budget - today_total_calories

    context = {
        "foods": foods,
        "today_consumption": today_consumption,
        "today_total_calories": today_total_calories,
        "base_rate": base_rate,
        "active_calories": active_calories,
        "active_is_estimate": active_is_estimate,
        "goal_deficit": goal_deficit,
        "effective_budget": effective_budget,
        "remaining_calories": remaining_calories,
        "view_date": view_date,
        "is_today": is_today,
        "prev_date": (view_date - timedelta(days=1)).isoformat(),
        "next_date": (view_date + timedelta(days=1)).isoformat(),
    }
    return render(request, "food_tracking/home.html", context)


def get_or_create_target(user: User) -> CalorieTarget:
    """Return the user's calorie target, creating a default if absent."""
    target, _ = CalorieTarget.objects.get_or_create(user=user)
    return target


@login_required
@require_http_methods(["POST"])
def delete_consumption(request: HttpRequest) -> JsonResponse:
    """Delete a consumption record via AJAX POST."""
    try:
        consumption_id = request.POST.get("consumption_id")

        if not consumption_id:
            return JsonResponse(
                {"success": False, "error": "Missing consumption_id"}, status=400
            )

        # Get consumption and verify it belongs to the current user
        consumption = Consumption.objects.get(id=consumption_id, user=request.user)
        consumption.delete()

        return JsonResponse({"success": True})
    except Consumption.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Consumption not found"}, status=404
        )
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


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

        try:
            day = get_requested_day(request)
        except ValueError:
            return JsonResponse({"success": False, "error": "Invalid date"}, status=400)

        food = Food.objects.get(id=food_id)
        consumption = Consumption.objects.create(
            user=request.user,
            food=food,
            quantity=Decimal(quantity),
            consumed_at=resolve_consumed_at(day),
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


def get_refinement_params(request: HttpRequest) -> tuple[dict[str, Any] | None, str]:
    """Extract optional refinement fields from an estimate request.

    Returns (previous_estimate, correction). Both must be present together —
    a correction without the prior estimate (or vice versa) raises ValueError,
    as does a previous_estimate that isn't a JSON object.
    """
    correction = request.POST.get("correction", "").strip()
    previous_raw = request.POST.get("previous_estimate", "").strip()

    if not correction and not previous_raw:
        return None, ""
    if not correction or not previous_raw:
        raise ValueError(
            "A refinement needs both a correction and the previous estimate."
        )

    try:
        previous_estimate = json.loads(previous_raw)
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid previous estimate.") from exc
    if not isinstance(previous_estimate, dict):
        raise ValueError("Invalid previous estimate.")
    return previous_estimate, correction


@login_required
@require_http_methods(["POST"])
def estimate(request: HttpRequest) -> JsonResponse:
    """Estimate calories from an uploaded photo or a text description.

    Optional correction + previous_estimate fields turn the request into a
    refinement: the original input is resent along with the prior estimate and
    the user's correction, and the model revises its numbers.

    Returns the estimate WITHOUT saving it; the client confirms/edits before
    calling log_estimate.
    """
    try:
        image = request.FILES.get("image")
        text = request.POST.get("text", "").strip()
        note = request.POST.get("note", "").strip()
        previous_estimate, correction = get_refinement_params(request)

        if image is not None:
            result = estimation.estimate_from_image(
                image.read(),
                image.content_type or "",
                note,
                previous_estimate=previous_estimate,
                correction=correction,
            )
        elif text:
            result = estimation.estimate_from_text(
                text, previous_estimate=previous_estimate, correction=correction
            )
        else:
            return JsonResponse(
                {"success": False, "error": "Provide an image or text."}, status=400
            )

        return JsonResponse({"success": True, "estimate": result.to_dict()})
    except ValueError as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def estimate_recipe(request: HttpRequest) -> JsonResponse:
    """Estimate calories for the eaten fraction of a pasted recipe (unsaved)."""
    try:
        recipe_text = request.POST.get("recipe_text", "").strip()
        fraction_raw = request.POST.get("fraction", "")

        if not recipe_text:
            return JsonResponse(
                {"success": False, "error": "Missing recipe text."}, status=400
            )

        try:
            fraction = float(fraction_raw)
        except (TypeError, ValueError):
            return JsonResponse(
                {"success": False, "error": "Invalid fraction."}, status=400
            )

        if not 0 < fraction <= 1:
            return JsonResponse(
                {"success": False, "error": "Fraction must be between 0 and 1."},
                status=400,
            )

        previous_estimate, correction = get_refinement_params(request)
        result = estimation.estimate_recipe(
            recipe_text,
            fraction,
            previous_estimate=previous_estimate,
            correction=correction,
        )
        return JsonResponse({"success": True, "estimate": result.to_dict()})
    except ValueError as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def log_estimate(request: HttpRequest) -> JsonResponse:
    """Save a confirmed ad-hoc estimate as a Consumption (no Food reference)."""
    try:
        description = request.POST.get("description", "").strip()
        calories_raw = request.POST.get("calories", "")

        if not description:
            return JsonResponse(
                {"success": False, "error": "Missing description."}, status=400
            )

        try:
            calories = Decimal(calories_raw)
        except (InvalidOperation, TypeError):
            return JsonResponse(
                {"success": False, "error": "Invalid calories."}, status=400
            )

        if calories < 0:
            return JsonResponse(
                {"success": False, "error": "Calories must be non-negative."},
                status=400,
            )

        try:
            day = get_requested_day(request)
        except ValueError:
            return JsonResponse({"success": False, "error": "Invalid date"}, status=400)

        consumption = Consumption.objects.create(
            user=request.user,
            food=None,
            description=description,
            calories=calories,
            notes=request.POST.get("notes", ""),
            consumed_at=resolve_consumed_at(day),
        )
        return JsonResponse(
            {"success": True, "consumption": consumption.to_dict_for_api()}
        )
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def set_target(request: HttpRequest) -> JsonResponse:
    """Set the user's single fixed daily calorie target."""
    try:
        target_raw = request.POST.get("daily_calorie_target", "")
        try:
            daily_target = int(target_raw)
        except (TypeError, ValueError):
            return JsonResponse(
                {"success": False, "error": "Invalid target."}, status=400
            )

        if daily_target <= 0:
            return JsonResponse(
                {"success": False, "error": "Target must be positive."}, status=400
            )

        target, _ = CalorieTarget.objects.update_or_create(
            user=request.user,
            defaults={"daily_calorie_target": daily_target},
        )
        return JsonResponse({"success": True, "target": target.to_dict_for_api()})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def set_goal_deficit(request: HttpRequest) -> JsonResponse:
    """Set the daily calorie deficit the user is aiming for."""
    try:
        deficit_raw = request.POST.get("goal_deficit", "")
        try:
            goal_deficit = int(deficit_raw)
        except (TypeError, ValueError):
            return JsonResponse(
                {"success": False, "error": "Invalid deficit."}, status=400
            )

        if goal_deficit < 0:
            return JsonResponse(
                {"success": False, "error": "Deficit must be non-negative."},
                status=400,
            )

        target, _ = CalorieTarget.objects.update_or_create(
            user=request.user,
            defaults={"goal_deficit": goal_deficit},
        )
        return JsonResponse({"success": True, "target": target.to_dict_for_api()})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def set_active_calories(request: HttpRequest) -> JsonResponse:
    """Set a day's Apple Watch active (Move ring) calories.

    Upserts a single DailyActiveCalories row for the requested Pacific day
    (default: today) so the user can log it once at the end of the day, correct
    it later, or fill in a day they forgot.
    """
    try:
        active_raw = request.POST.get("active_calories", "")
        try:
            active_calories = int(active_raw)
        except (TypeError, ValueError):
            return JsonResponse(
                {"success": False, "error": "Invalid active calories."}, status=400
            )

        if active_calories < 0:
            return JsonResponse(
                {"success": False, "error": "Active calories must be non-negative."},
                status=400,
            )

        try:
            day = get_requested_day(request)
        except ValueError:
            return JsonResponse({"success": False, "error": "Invalid date"}, status=400)

        entry, _ = DailyActiveCalories.objects.update_or_create(
            user=request.user,
            date=day,
            defaults={"active_calories": active_calories},
        )
        return JsonResponse({"success": True, "active": entry.to_dict_for_api()})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)
