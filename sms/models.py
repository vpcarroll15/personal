"""
Models for the SMS app.
"""

from datetime import timedelta

from django.apps import apps
from django.conf import settings
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField

THREE_MONTHS_IN_DAYS = 3 * 30


def create_prayer_snippet(prayer_type, data_point):
    """
    Create a prayer snippet from a DataPoint.

    A very simple callback function that loads the PrayerSnippet model and maps
    fields from the DataPoint to the PrayerSnippet. We have to load the model because
    otherwise we have a circular dependency between models.py files.
    """
    if data_point.text:
        prayer_snippet_model = apps.get_model("prayer", "PrayerSnippet")

        # Clamp dynamic weight to the appropriate range.
        dynamic_weight = data_point.score if data_point.score else 1
        dynamic_weight = min(max(dynamic_weight, 10), 1)

        prayer_snippet_model.objects.update_or_create(
            # the sms_data_point is the unique key that should never create more than one message.
            sms_data_point=data_point,
            defaults=dict(
                user=data_point.user.logged_in_user,
                text=data_point.text,
                type=prayer_type,
                dynamic_weight=dynamic_weight,
                # Make sure to set some expiration time because otherwise the contents of these prayers
                # become painfully outdated after a while.
                expires_at=data_point.created_at + timedelta(days=THREE_MONTHS_IN_DAYS),
            ),
        )


def create_gratitude_prayer_snippet(data_point):
    create_prayer_snippet("GRATITUDE", data_point)


def create_request_prayer_snippet(data_point):
    create_prayer_snippet("REQUEST", data_point)


def create_praise_prayer_snippet(data_point):
    create_prayer_snippet("PRAISE", data_point)


callbacks_pool = {
    "create_gratitude_prayer_snippet": create_gratitude_prayer_snippet,
    "create_request_prayer_snippet": create_request_prayer_snippet,
    "create_praise_prayer_snippet": create_praise_prayer_snippet,
}


class Question(models.Model):
    """Represents one question that we might want to ask a user."""

    # This is the max length of an ASCII SMS.
    text = models.CharField(max_length=160)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    min_score = models.SmallIntegerField(default=0)
    max_score = models.SmallIntegerField(default=10)

    callback = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        choices=[(id, id) for id in callbacks_pool.keys()],
        help_text=(
            "If defined, then this represents a callback function that we should trigger when we create "
            "a DataPoint for this question. The signature of the callback is `callback(data_point: DataPoint)`."
        ),
    )

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
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )

    phone_number = PhoneNumberField(unique=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    send_message_at_time = models.DateTimeField(auto_now_add=True)

    # How long the user has to reply to texts before replies will be
    # rejected.
    expire_message_after = models.DurationField(
        default=timedelta(minutes=15),
    )

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

    def save(self, *args, **kwargs):
        """Make sure that we trigger the callback if it's defined."""
        super().save(*args, **kwargs)
        if self.question.callback:
            callback = callbacks_pool.get(self.question.callback)
            if callback is not None:
                callback(self)

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
