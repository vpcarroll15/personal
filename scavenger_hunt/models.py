from django.db import models

from django.contrib.postgres.fields import ArrayField


class Location(models.Model):
    """Represents one target in a scavenger hunt."""
    latitude = models.FloatField()
    longitude = models.FloatField()

    clue = models.TextField()

    name = models.CharField(
        max_length=200,
        help_text="This will never be displayed to the user. It is only used in the admin.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class ScavengerHuntTemplate(models.Model):
    """A description of a scavenger hunt that someone could start."""
    # The list of location ids, in order, that we are supposed to visit on this hunt.
    location_ids = ArrayField(models.IntegerField(), default=list)

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class ScavengerHunt(models.Model):
    """Represents a scavenger hunt in progress."""
    hunt = models.ForeignKey("ScavengerHuntTemplate", on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    current_location = models.ForeignKey("Location", on_delete=models.CASCADE)

    def __str__(self):
        return "{}, {}".format(self.hunt, self.current_location)
