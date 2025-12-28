from datetime import datetime, timezone

import arrow
from django import template

register = template.Library()


@register.filter
def human_readable_how_long_ago(supplied_datetime: datetime) -> str:
    """Converts a datetime to human-readable relative time (e.g., '5 days ago')."""
    arrow_datetime = arrow.get(supplied_datetime)
    return arrow_datetime.humanize()
