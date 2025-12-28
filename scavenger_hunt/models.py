from typing import Any

from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models
from geographiclib.geodesic import Geodesic

# Constants for heading calculations
HEADING_LABELS = [
    "north",
    "northeast",
    "east",
    "southeast",
    "south",
    "southwest",
    "west",
    "northwest",
]
DEGREES_PER_LABEL = 360 / len(HEADING_LABELS)

# Field length constants
NAME_MAX_LENGTH = 200
PATH_TO_STATIC_IMG_ASSET_MAX_LENGTH = 200
SOLUTION_MAX_LENGTH = 200

# Location defaults
DEFAULT_RADIUS_METERS = 30


class UnknownLocationException(Exception):
    """We throw this if someone tries to compute distance to a location with unspecified coordinates."""


class Location(models.Model):
    """Represents one target in a scavenger hunt."""

    class Meta:
        ordering = ["name"]
        verbose_name = "Location"
        verbose_name_plural = "Locations"

    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    clue = models.TextField(blank=True)
    hint = models.TextField(null=True, blank=True)
    post_solve = models.TextField(
        null=True,
        blank=True,
        help_text="We show the user this text if they successfully solve the clue, before progressing to the next clue.",
    )

    name = models.CharField(
        max_length=NAME_MAX_LENGTH,
        help_text="This will never be displayed to the user. It is only used in the admin.",
    )

    radius = models.IntegerField(
        default=DEFAULT_RADIUS_METERS,
        help_text=(
            "How close the user needs to be in meters to the coordinate in order to advance. This will have no meaning if lat/lng aren't provided."
        ),
    )

    path_to_static_img_asset = models.CharField(
        null=True,
        blank=True,
        max_length=PATH_TO_STATIC_IMG_ASSET_MAX_LENGTH,
        help_text="This should point to a static image asset. Optional.",
    )

    disable_heading = models.BooleanField(
        default=False,
        help_text="If true, disables the ability to compute a heading to this destination.",
    )

    solutions = ArrayField(
        models.CharField(max_length=SOLUTION_MAX_LENGTH),
        null=True,
        blank=True,
        help_text="If provided, the user must input one of these in order to move on to the next section.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        if not self.solutions and self.latitude is None:
            raise ValidationError("Either a coordinate or a solution must be provided.")
        if not self.clue and not self.path_to_static_img_asset:
            raise ValidationError("Either a clue or an image must be provided.")
        if (self.latitude and self.longitude is None) or (
            self.latitude is None and self.longitude
        ):
            raise ValidationError(
                "If you provide one of lat/lng, you must provide the other."
            )


class ScavengerHuntTemplate(models.Model):
    """A description of a scavenger hunt that someone could start."""

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "Scavenger Hunt Template"
        verbose_name_plural = "Scavenger Hunt Templates"

    # The list of location ids, in order, that we are supposed to visit on this hunt.
    location_ids = ArrayField(models.IntegerField(), default=list)

    name = models.CharField(max_length=NAME_MAX_LENGTH)
    description = models.TextField(blank=True)

    finished_message = models.TextField(
        blank=True,
        help_text="The user will read this if they complete your hunt.",
    )

    path_to_static_img_asset = models.CharField(
        null=True,
        blank=True,
        max_length=PATH_TO_STATIC_IMG_ASSET_MAX_LENGTH,
        help_text="This should point to a static image asset. Optional.",
    )
    skip_all_checks = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name


class ScavengerHunt(models.Model):
    """Represents a scavenger hunt in progress."""

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Scavenger Hunt"
        verbose_name_plural = "Scavenger Hunts"

    hunt_template = models.ForeignKey("ScavengerHuntTemplate", on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # The list of location ids, in order, that we are supposed to visit on this hunt.
    location_ids = ArrayField(models.IntegerField(), default=list)
    current_location = models.ForeignKey(
        "Location", null=True, on_delete=models.CASCADE
    )

    post_location_phase = models.BooleanField(default=False)
    is_finished = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"{self.hunt_template}, {self.current_location}"

    def distance_and_direction_to_current_location(
        self, latitude: float, longitude: float
    ) -> tuple[float, str]:
        """ "
        Returns the distance in meters to the current location, and the direction as a string: "WEST," "NORTHWEST," etc.
        """
        assert self.current_location is not None
        if (
            self.current_location.latitude is None
            or self.current_location.longitude is None
        ):
            raise UnknownLocationException("Lat/lng of target is unknown.")

        out_dict = Geodesic.WGS84.Inverse(
            latitude,
            longitude,
            self.current_location.latitude,
            self.current_location.longitude,
        )
        distance_m = out_dict["s12"]
        heading_from_north = out_dict["azi1"]
        if heading_from_north < 0.0:
            heading_from_north += 360

        # We have to add a weird little offset because "north" doesn't start at 0 degrees. It starts at
        # -22.5 degrees.
        offset_heading = heading_from_north + (DEGREES_PER_LABEL / 2)
        if offset_heading > 360:
            offset_heading -= 360
        index_in_heading_labels = int(offset_heading / DEGREES_PER_LABEL)
        return distance_m, HEADING_LABELS[index_in_heading_labels]

    def location_is_completed(
        self, latitude: float, longitude: float, solution: str
    ) -> bool:
        """
        Return True if, according to our coordinates and the user-provided solution, we should advance to the next location.
        """
        if self.hunt_template.skip_all_checks:
            return True
        if self.post_location_phase:
            return True
        try:
            distance, _ = self.distance_and_direction_to_current_location(
                latitude, longitude
            )
        except UnknownLocationException:
            pass
        else:
            if distance > self.current_location.radius:
                return False
        if self.current_location.solutions:
            for correct_answer in self.current_location.solutions:
                if correct_answer.casefold() == solution.casefold():
                    return True
            return False
        return True
