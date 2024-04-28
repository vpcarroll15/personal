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
    return date.fromisoformat(value)


@dataclass
class User:
    id: int
    phone_number: str
    start_text_hour: int
    end_text_hour: int
    last_start_text_sent_date: date = field(metadata={"converter": date_converter})
    last_end_text_sent_date: date = field(metadata={"converter": date_converter})
    timezone: pytz.timezone = field(metadata={"converter": pytz.timezone})
    possible_focus_areas: list[str]

    @property
    def now(self) -> datetime:
        return datetime.now(tz=self.timezone)

    @property
    def should_start_checkin(self) -> bool:
        return (
            self.last_start_text_sent_date < self.now.date()
            and self.start_text_hour < self.now.hour
        )
