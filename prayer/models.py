import random

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class PrayerType(models.TextChoices):
    GRATITUDE = "1", "GRATITUDE"
    REQUEST = "2", "REQUEST"
    PRAISE = "3", "PRAISE"


class PrayerSchema(models.Model):
    """
    The schema that we use to generate a prayer.
    """

    logged_in_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
    )
    name = models.TextField(help_text="The name of the prayer.")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    schema = models.JSONField(
        help_text=(
            "The schema that we use to generate the prayer. "
            "It should look like this: "
            "{'snippets': [{'type': 'GRATITUDE', 'count': 3}, {'type': 'PRAISE', 'count': 1}]}"
        )
    )


class PrayerSnippet(models.Model):

    text = models.TextField(help_text="The content of the snippet, which becomes part of the prayer.")
    type = models.CharField(
        max_length=20,
        choices=PrayerType.choices,
        help_text="The type of snippet."
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this snippet expires."
    )
    weighting = models.SmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        default=1,
        blank=True,
        help_text="The value of this snippet from 1 to 10.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def sample(self):
        """Sample the snippet according to its weighting and return a score from 0 to 1."""
        return max(random.random() for _ in range(self.weighting))
