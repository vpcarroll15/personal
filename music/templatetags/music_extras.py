from datetime import datetime, timezone

import arrow
from django import template

register = template.Library()


@register.filter
def human_readable_how_long_ago(supplied_datetime):
    arrow_datetime = arrow.get(supplied_datetime)
    return arrow_datetime.humanize()
