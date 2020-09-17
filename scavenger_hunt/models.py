from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models
from geographiclib.geodesic import Geodesic


HEADING_LABELS = ["north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest"]
DEGREES_PER_LABEL = 360 / len(HEADING_LABELS)


class UnknownLocationException(Exception):
    """We throw this if someone tries to compute distance to a location with unspecified coordinates."""


class Location(models.Model):
    """Represents one target in a scavenger hunt."""
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    clue = models.TextField(blank=True)
    hint = models.TextField(null=True, blank=True)

    name = models.CharField(
        max_length=200,
        help_text="This will never be displayed to the user. It is only used in the admin.",
    )

    radius = models.IntegerField(default=30, help_text=(
        "How close the user needs to be in meters to the coordinate in order to advance. This will have no meaning if lat/lng aren't provided."
    ))

    path_to_static_img_asset = models.CharField(
        null=True, blank=True, max_length=200, help_text="This should point to a static image asset. Optional."
    )

    disable_heading = models.BooleanField(default=False, help_text="If true, disables the ability to compute a heading to this destination.")

    solution = models.CharField(
        null=True, blank=True, max_length=200, help_text="If provided, the user must input this in order to move on to the next section."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def clean(self):
        if not self.solution and self.latitude is None:
            raise ValidationError("Either a coordinate or a solution must be provided.")
        if not self.clue and not self.path_to_static_img_asset:
            raise ValidationError("Either a clue or an image must be provided.")
        if (self.latitude and self.longitude is None) or (self.latitude is None and self.longitude):
            raise ValidationError("If you provide one of lat/lng, you must provide the other.")


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

    # The list of location ids, in order, that we are supposed to visit on this hunt.
    location_ids = ArrayField(models.IntegerField(), default=list)
    current_location = models.ForeignKey("Location", null=True, on_delete=models.CASCADE)

    is_finished = models.BooleanField(default=False)

    def __str__(self):
        return "{}, {}".format(self.hunt_template, self.current_location)
    
    def distance_and_direction_to_current_location(self, latitude, longitude):
        """"
        Returns the distance in meters to the current location, and the direction as a string: "WEST," "NORTHWEST," etc.
        """
        assert self.current_location is not None
        if self.current_location.latitude is None or self.current_location.longitude is None:
            raise UnknownLocationException("Lat/lng of target is unknown.")

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

    
    def should_advance_to_next_location(self, latitude, longitude, solution):
        """
        Return True if, according to our coordinates and the user-provided solution, we should advance to the next location.
        """
        try:
            distance, _ = self.distance_and_direction_to_current_location(latitude, longitude)
        except UnknownLocationException:
            pass
        else:
            if distance > self.current_location.radius:
                return False
        if self.current_location.solution and self.current_location.solution.casefold() != solution.casefold():
            return False
        return True
    