"""
The types used by sms_app_manager_main.py.

This will strongly resemble what is defined in sms/models.py, but without
dependencies on Django or web stuff. We will often serialize into or
deserialize from these classes.
"""

from dataclasses import dataclass
from datetime import datetime

import dateutil.parser


def datetime_converter(value: str | datetime) -> datetime:
    if isinstance(value, str):
        return dateutil.parser.parse(value)
    return value


@dataclass
class Question:
    id: int
    text: str
    min_score: int
    max_score: int


@dataclass
class User:
    id: int
    phone_number: str
    send_message_at_time: datetime
    questions: list[Question]
    start_text_hour: int
    end_text_hour: int
    timezone: str
    text_every_n_days: int

    def __post_init__(self) -> None:
        self.send_message_at_time = datetime_converter(self.send_message_at_time)
        # Convert question dicts to Question objects if needed
        if self.questions and isinstance(self.questions[0], dict):
            self.questions = [Question(**q) for q in self.questions]  # type: ignore[arg-type]
