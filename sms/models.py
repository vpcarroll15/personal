"""
Models for the SMS app.
"""
from datetime import timedelta

from django.conf import settings
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField


class Question(models.Model):
    """Represents one question that we might want to ask a user."""

    # This is the max length of an ASCII SMS.
    text = models.CharField(max_length=160)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    min_score = models.SmallIntegerField(default=0)
    max_score = models.SmallIntegerField(default=10)

    def __str__(self):
        return self.text

    def to_dict_for_api(self):
        return dict(
            id=self.id,
            text=self.text,
            max_score=self.max_score,
            min_score=self.min_score,
        )


class User(models.Model):
    """Represents one user of the app."""

    logged_in_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
    )

    phone_number = PhoneNumberField(unique=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    send_message_at_time = models.DateTimeField(auto_now_add=True)

    # How long the user has to reply to texts before replies will be
    # rejected.
    expire_message_after = models.DurationField(default=timedelta(minutes=15),)

    # Don't text this user before this time in the morning.
    start_text_hour = models.SmallIntegerField(default=7)
    # Don't text this user after this time at night.
    end_text_hour = models.SmallIntegerField(default=22)
    # This should be the name of a pytz timezone.
    timezone = models.CharField(max_length=100, default="America/Los_Angeles")
    text_every_n_days = models.SmallIntegerField(default=1)

    questions = models.ManyToManyField(Question)

    def __str__(self):
        return str(self.phone_number)

    def to_dict_for_api(self):
        return dict(
            id=self.id,
            phone_number=str(self.phone_number),
            send_message_at_time=self.send_message_at_time.isoformat(),
            questions=[question.to_dict_for_api() for question in self.questions.all()],
            start_text_hour=self.start_text_hour,
            end_text_hour=self.end_text_hour,
            timezone=self.timezone,
            text_every_n_days=self.text_every_n_days,
        )


class DataPoint(models.Model):
    """Represents one collected response to one Question."""

    class Meta:
        # We expect to be doing a lot of queries like "give me the most
        # recent DataPoints for this user."
        indexes = [
            models.Index(fields=["user", "-created_at"]),
        ]

    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Aggregation queries should ignore all DataPoints where score = null.
    score = models.SmallIntegerField(blank=True, null=True)

    # This is used for unstructured text that the user may send back
    # in addition to a score.
    text = models.TextField(blank=True, null=True)

    # This short ID is given to us by Twilio when we get a message response.
    # It is guaranteed to be less than 40 chars long.
    response_message_id = models.CharField(max_length=40, blank=True, null=True)

    def __str__(self):
        return f"{self.user.phone_number}, {self.question.text}, {self.score}"

    def to_dict_for_api(self):
        return dict(
            id=self.id,
            question_id=self.question_id,
            user_id=self.user_id,
            response_message_id=self.response_message_id,
            created_at=self.created_at.isoformat(),
            updated_at=self.updated_at.isoformat(),
            score=self.score,
            text=self.text,
        )
