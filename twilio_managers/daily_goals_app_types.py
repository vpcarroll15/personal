"""
The types used by daily_goals_app_manager_main.py.

This will strongly resemble what is defined in daily_goals/models.py, but without
dependencies on Django or web stuff. We will often serialize into or
deserialize from these classes.
"""
from dataclasses import dataclass, field
from datetime import date, datetime

import pytz


def date_converter(value):
    if isinstance(value, str):
        return date.fromisoformat(value)
    else:
        return value


def datetime_converter(value):
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    else:
        return value


def timezone_converter(value):
    if isinstance(value, str):
        return pytz.timezone(value)
    else:
        return value


@dataclass
class User:
    id: int
    phone_number: str
    start_text_hour: int
    end_text_hour: int
    last_start_text_sent_date: date
    last_end_text_sent_date: date
    timezone: pytz.timezone
    possible_focus_areas: list[str]
    ai_prompt: str = ""

    def __post_init__(self):
        self.last_start_text_sent_date = date_converter(self.last_start_text_sent_date)
        self.last_end_text_sent_date = date_converter(self.last_end_text_sent_date)
        self.timezone = timezone_converter(self.timezone)

    @property
    def now(self) -> datetime:
        return datetime.now(tz=self.timezone)

    @property
    def should_start_checkin(self) -> bool:
        return (
            self.last_start_text_sent_date < self.now.date()
            and self.start_text_hour <= self.now.hour
        )


@dataclass
class DailyCheckin:
    id: int
    user_id: int
    response_message_id: str | None
    created_at: datetime
    updated_at: datetime
    possible_focus_areas: list[str]
    chosen_focus_areas: list[str] | None = None

    def __post_init__(self):
        self.created_at = datetime_converter(self.created_at)
        self.updated_at = datetime_converter(self.updated_at)
