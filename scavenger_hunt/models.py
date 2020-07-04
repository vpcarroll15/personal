from django.db import models
from django.contrib.postgres.fields import ArrayField
from geographiclib.geodesic import Geodesic


HEADING_LABELS = ["north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest"]
DEGREES_PER_LABEL = 360 / len(HEADING_LABELS)


class Location(models.Model):
    """Represents one target in a scavenger hunt."""
    latitude = models.FloatField()
    longitude = models.FloatField()

    clue = models.TextField(blank=True)

    name = models.CharField(
        max_length=200,
        help_text="This will never be displayed to the user. It is only used in the admin.",
    )

    radius = models.IntegerField(default=30, help_text=(
        "How close the user needs to be in meters to the coordinate in order to advance."
    ))

    path_to_static_img_asset = models.CharField(
        null=True, blank=True, max_length=200, help_text="This should point to a static image asset. Optional."
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

    finished_message = models.TextField(
        blank=True, help_text="The user will read this if they complete your hunt.",
    )

    path_to_static_img_asset = models.CharField(
        null=True, blank=True, max_length=200, help_text="This should point to a static image asset. Optional."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class ScavengerHunt(models.Model):
    """Represents a scavenger hunt in progress."""
    hunt_template = models.ForeignKey("ScavengerHuntTemplate", on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    current_location = models.ForeignKey("Location", null=True, on_delete=models.CASCADE)

    is_finished = models.BooleanField(default=False)

    def __str__(self):
        return "{}, {}".format(self.hunt_template, self.current_location)
    
    def distance_and_direction_to_current_location(self, latitude, longitude):
        """"
        Returns the distance in meters to the current location, and the direction as a string: "WEST," "NORTHWEST," etc.
        """
        assert self.current_location is not None
        out_dict = Geodesic.WGS84.Inverse(
            latitude, longitude, self.current_location.latitude, self.current_location.longitude
        )
        distance_m = out_dict["s12"]
        heading_from_north = out_dict["azi1"]
        if heading_from_north < 0.0:
            heading_from_north += 360

        # We have to add a weird little offset because "north" doesn't start at 0 degrees. It starts at
        # -22.5 degrees.
        offset_heading = (heading_from_north + (DEGREES_PER_LABEL / 2))
        if offset_heading > 360:
            offset_heading -= 360
        index_in_heading_labels =  int(offset_heading / DEGREES_PER_LABEL)
        return distance_m, HEADING_LABELS[index_in_heading_labels]

    
    def should_advance_to_next_location(self, latitude, longitude):
        """
        Return True if, according to our coordinates, we should advance to the next location.
        """
        distance, _ = self.distance_and_direction_to_current_location(latitude, longitude)
        return distance < self.current_location.radius
    