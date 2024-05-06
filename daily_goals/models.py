"""
Models for the daily_goals app.
"""
from datetime import date
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
    # Keep track of which texts we have sent on which days.
    last_start_text_sent_date = models.DateField(
        default=date(year=2021, month=1, day=1)
    )
    last_end_text_sent_date = models.DateField(default=date(year=2021, month=1, day=1))

    timezone = models.TextField(default="America/Los_Angeles")

    possible_focus_areas = ArrayField(
        base_field=models.TextField(),
    )

    ai_prompt = models.TextField(default="")

    def __str__(self):
        return str(self.phone_number)

    def to_dict_for_api(self):
        return dict(
            id=self.id,
            phone_number=str(self.phone_number),
            start_text_hour=self.start_text_hour,
            end_text_hour=self.end_text_hour,
            last_start_text_sent_date=str(self.last_start_text_sent_date),
            last_end_text_sent_date=str(self.last_end_text_sent_date),
            timezone=self.timezone,
            possible_focus_areas=self.possible_focus_areas,
            ai_prompt=self.ai_prompt,
        )


class DailyCheckin(models.Model):
    """Represents the accumulated daily interaction with a user throughout the day."""

    class Meta:
        # We expect to be doing a lot of queries like "give me the most
        # recent DailyCheckin for this user."
        indexes = [
            models.Index(fields=["user", "-created_at"]),
        ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    possible_focus_areas = ArrayField(
        base_field=models.TextField(),
        help_text="The focus areas the user could choose from (suggested by default).",
    )
    chosen_focus_areas = ArrayField(
        base_field=models.TextField(),
        null=True,
        blank=True,
        help_text="The focus areas the user chose to focus on today.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # This short ID is given to us by Twilio when we get a message response.
    # It is guaranteed to be less than 40 chars long.
    response_message_id = models.CharField(max_length=40, blank=True, null=True)

    def __str__(self):
        return f"{self.user.phone_number}, {self.created_at}"

    def to_dict_for_api(self):
        return dict(
            id=self.id,
            user_id=self.user_id,
            response_message_id=self.response_message_id,
            created_at=self.created_at.isoformat(),
            updated_at=self.updated_at.isoformat(),
            possible_focus_areas=self.possible_focus_areas,
        )
