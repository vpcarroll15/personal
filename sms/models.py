"""
Models for the SMS app.
"""

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


class User(models.Model):
    """Represents one user of the app."""
    phone_number = PhoneNumberField(unique=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    send_message_at_time = models.DateTimeField(auto_now_add=True)

    questions = models.ManyToManyField(Question)

    def __str__(self):
        return str(self.phone_number)


class DataPoint(models.Model):
    """Represents one collected response to one Question."""
    class Meta:
        # We expect to be doing a lot of queries like "give me the most 
        # recent DataPoints for this user."
        indexes = [
            models.Index(fields=['user', '-created_at']),
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
    