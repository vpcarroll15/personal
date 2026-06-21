# Grid and display constants
DEFAULT_RECENT_CONSUMPTION_LIMIT = 10
DEFAULT_REPORT_DAYS = 7

# Number of prior days averaged to estimate active calories on an unlogged day
ACTIVE_CALORIES_WINDOW_DAYS = 14
# Minimum logged days in the window required before trusting the average;
# below this we fall back to DEFAULT_ACTIVE_CALORIES_ESTIMATE.
MIN_LOGGED_DAYS_FOR_ESTIMATE = 3
DEFAULT_ACTIVE_CALORIES_ESTIMATE = 500

# Calorie aggregation periods
PERIOD_DAY = "day"
PERIOD_WEEK = "week"
PERIOD_MONTH = "month"

VALID_PERIODS = [PERIOD_DAY, PERIOD_WEEK, PERIOD_MONTH]

# Default foods for initial setup
DEFAULT_FOODS = [
    {
        "name": "Pecans",
        "icon": "🌰",
        "serving_size": "1 oz",
        "calories_per_serving": 189,
        "display_order": 1,
    },
    {
        "name": "Cashews",
        "icon": "🌙",
        "serving_size": "1 oz",
        "calories_per_serving": 154,
        "display_order": 2,
    },
    {
        "name": "Peanuts",
        "icon": "🥜",
        "serving_size": "1 oz",
        "calories_per_serving": 159,
        "display_order": 3,
    },
    {
        "name": "Dried Figs",
        "icon": "🫐",
        "serving_size": "1 dried fig",
        "calories_per_serving": 20,
        "display_order": 4,
    },
]
