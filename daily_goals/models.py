"""
Models for the daily_goals app.
"""
from django.conf import settings
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
from django.contrib.postgres.fields import ArrayField


class User(models.Model):
    """Represents one user of the app."""

    logged_in_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="daily_goals_user_set",
    )

    phone_number = PhoneNumberField(unique=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    start_text_hour = models.SmallIntegerField(
        help_text="The time of day to send the goal solicitation text, in 24-hour format. 0-23"
    )
    end_text_hour = models.SmallIntegerField(
        help_text="The time of day to send the goal recap text, in 24-hour format. 0-23"
    )
    timezone = models.TextField(default="America/Los_Angeles")

    possible_focus_areas = ArrayField(
        base_field=models.TextField(),
    )

    def __str__(self):
        return str(self.phone_number)

    def to_dict_for_api(self):
        return dict(
            id=self.id,
            phone_number=str(self.phone_number),
            start_text_hour=self.start_text_hour,
            end_text_hour=self.end_text_hour,
            timezone=self.timezone,
            possible_focus_areas=self.possible_focus_areas,
        )
