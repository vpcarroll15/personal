from django.core.exceptions import ValidationError
from django.test import Client, TestCase

from scavenger_hunt.models import (
    Location,
    ScavengerHunt,
    ScavengerHuntTemplate,
    UnknownLocationException,
)


class LocationModelTests(TestCase):
    """Tests for Location model methods."""

    def test_location_str(self):
        """Test the __str__ method of Location."""
        location = Location.objects.create(
            name="Test Location",
            latitude=40.7128,
            longitude=-74.0060,
            clue="Find the place",
        )
        self.assertEqual(str(location), "Test Location")

    def test_clean_requires_either_coordinate_or_solution(self):
        """Test that clean() raises ValidationError if neither coordinate nor solution provided."""
        location = Location(name="Test", clue="Test clue")
        with self.assertRaises(ValidationError) as cm:
            location.clean()
        self.assertIn(
            "Either a coordinate or a solution must be provided", str(cm.exception)
        )

    def test_clean_requires_either_clue_or_image(self):
        """Test that clean() raises ValidationError if neither clue nor image provided."""
        location = Location(
            name="Test",
            latitude=40.7128,
            longitude=-74.0060,
        )
        with self.assertRaises(ValidationError) as cm:
            location.clean()
        self.assertIn("Either a clue or an image must be provided", str(cm.exception))

    def test_clean_requires_both_lat_and_lng(self):
        """Test that clean() raises ValidationError if only one of lat/lng provided."""
        location = Location(
            name="Test",
            latitude=40.7128,
            clue="Test clue",
        )
        with self.assertRaises(ValidationError) as cm:
            location.clean()
        self.assertIn(
            "If you provide one of lat/lng, you must provide the other",
            str(cm.exception),
        )

    def test_clean_passes_with_valid_coordinate_and_clue(self):
        """Test that clean() passes with valid coordinate and clue."""
        location = Location(
            name="Test",
            latitude=40.7128,
            longitude=-74.0060,
            clue="Test clue",
        )
        location.clean()  # Should not raise

    def test_clean_passes_with_solutions(self):
        """Test that clean() passes with solutions."""
        location = Location(
            name="Test",
            clue="Test clue",
            solutions=["answer1", "answer2"],
        )
        location.clean()  # Should not raise


class ScavengerHuntTemplateModelTests(TestCase):
    """Tests for ScavengerHuntTemplate model methods."""

    def test_template_str(self):
        """Test the __str__ method of ScavengerHuntTemplate."""
        template = ScavengerHuntTemplate.objects.create(
            name="Test Hunt",
            description="A test scavenger hunt",
        )
        self.assertEqual(str(template), "Test Hunt")


class ScavengerHuntModelTests(TestCase):
    """Tests for ScavengerHunt model methods."""

    @classmethod
    def setUpTestData(cls):
        # Create test locations
        cls.location1 = Location.objects.create(
            name="Location 1",
            latitude=40.7128,
            longitude=-74.0060,
            clue="Clue 1",
            radius=30,
        )
        cls.location2 = Location.objects.create(
            name="Location 2",
            latitude=40.7589,
            longitude=-73.9851,
            clue="Clue 2",
            radius=50,
            solutions=["answer", "correct"],
        )
        cls.location3 = Location.objects.create(
            name="Location 3 (no coords)",
            clue="Clue 3",
            solutions=["solution"],
        )
        # Create template
        cls.template = ScavengerHuntTemplate.objects.create(
            name="Test Hunt Template",
            location_ids=[cls.location1.id, cls.location2.id],
        )

    def test_hunt_str(self):
        """Test the __str__ method of ScavengerHunt."""
        hunt = ScavengerHunt.objects.create(
            hunt_template=self.template,
            current_location=self.location1,
            location_ids=[self.location1.id],
        )
        result = str(hunt)
        self.assertIn("Test Hunt Template", result)
        self.assertIn("Location 1", result)

    def test_distance_and_direction_north(self):
        """Test distance_and_direction_to_current_location returns correct north direction."""
        hunt = ScavengerHunt.objects.create(
            hunt_template=self.template,
            current_location=self.location1,
            location_ids=[self.location1.id],
        )
        # Position south of target (should point north)
        distance, direction = hunt.distance_and_direction_to_current_location(
            40.70, -74.0060
        )
        self.assertGreater(distance, 0)
        self.assertEqual(direction, "north")

    def test_distance_and_direction_south(self):
        """Test distance_and_direction_to_current_location returns correct south direction."""
        hunt = ScavengerHunt.objects.create(
            hunt_template=self.template,
            current_location=self.location1,
            location_ids=[self.location1.id],
        )
        # Position north of target (should point south)
        distance, direction = hunt.distance_and_direction_to_current_location(
            40.73, -74.0060
        )
        self.assertGreater(distance, 0)
        self.assertEqual(direction, "south")

    def test_distance_and_direction_east(self):
        """Test distance_and_direction_to_current_location returns correct east direction."""
        hunt = ScavengerHunt.objects.create(
            hunt_template=self.template,
            current_location=self.location1,
            location_ids=[self.location1.id],
        )
        # Position west of target (should point east)
        distance, direction = hunt.distance_and_direction_to_current_location(
            40.7128, -74.02
        )
        self.assertGreater(distance, 0)
        self.assertEqual(direction, "east")

    def test_distance_and_direction_west(self):
        """Test distance_and_direction_to_current_location returns correct west direction."""
        hunt = ScavengerHunt.objects.create(
            hunt_template=self.template,
            current_location=self.location1,
            location_ids=[self.location1.id],
        )
        # Position east of target (should point west)
        distance, direction = hunt.distance_and_direction_to_current_location(
            40.7128, -73.99
        )
        self.assertGreater(distance, 0)
        self.assertEqual(direction, "west")

    def test_distance_and_direction_raises_for_unknown_location(self):
        """Test distance_and_direction raises UnknownLocationException for location without coords."""
        hunt = ScavengerHunt.objects.create(
            hunt_template=self.template,
            current_location=self.location3,  # No lat/lng
            location_ids=[self.location3.id],
        )
        with self.assertRaises(UnknownLocationException):
            hunt.distance_and_direction_to_current_location(40.7128, -74.0060)

    def test_location_is_completed_skip_all_checks(self):
        """Test location_is_completed returns True when skip_all_checks is enabled."""
        template = ScavengerHuntTemplate.objects.create(
            name="Skip Template",
            location_ids=[self.location1.id],
            skip_all_checks=True,
        )
        hunt = ScavengerHunt.objects.create(
            hunt_template=template,
            current_location=self.location1,
            location_ids=[self.location1.id],
        )
        self.assertTrue(hunt.location_is_completed(0, 0, ""))

    def test_location_is_completed_post_location_phase(self):
        """Test location_is_completed returns True in post_location_phase."""
        hunt = ScavengerHunt.objects.create(
            hunt_template=self.template,
            current_location=self.location1,
            location_ids=[self.location1.id],
            post_location_phase=True,
        )
        self.assertTrue(hunt.location_is_completed(0, 0, ""))

    def test_location_is_completed_too_far_away(self):
        """Test location_is_completed returns False when too far from location."""
        hunt = ScavengerHunt.objects.create(
            hunt_template=self.template,
            current_location=self.location1,
            location_ids=[self.location1.id],
        )
        # Far away coordinates
        self.assertFalse(hunt.location_is_completed(41.0, -75.0, ""))

    def test_location_is_completed_correct_solution(self):
        """Test location_is_completed returns True with correct solution."""
        hunt = ScavengerHunt.objects.create(
            hunt_template=self.template,
            current_location=self.location2,
            location_ids=[self.location2.id],
        )
        # Correct solution (case insensitive) - must be close enough to location too
        self.assertTrue(hunt.location_is_completed(40.7589, -73.9851, "ANSWER"))
        self.assertTrue(hunt.location_is_completed(40.7589, -73.9851, "correct"))

    def test_location_is_completed_incorrect_solution(self):
        """Test location_is_completed returns False with incorrect solution."""
        hunt = ScavengerHunt.objects.create(
            hunt_template=self.template,
            current_location=self.location2,
            location_ids=[self.location2.id],
        )
        self.assertFalse(hunt.location_is_completed(0, 0, "wrong"))

    def test_location_is_completed_no_solution_needed(self):
        """Test location_is_completed returns True when close enough and no solution needed."""
        hunt = ScavengerHunt.objects.create(
            hunt_template=self.template,
            current_location=self.location1,
            location_ids=[self.location1.id],
        )
        # Very close to location
        self.assertTrue(hunt.location_is_completed(40.7128, -74.0060, ""))

    def test_location_is_completed_solution_only_location(self):
        """Test location_is_completed with location that has solutions but no coordinates."""
        hunt = ScavengerHunt.objects.create(
            hunt_template=self.template,
            current_location=self.location3,  # Has solutions but no coords
            location_ids=[self.location3.id],
        )
        # Should succeed with correct solution regardless of coordinates
        self.assertTrue(hunt.location_is_completed(0, 0, "solution"))
        # Should fail with incorrect solution
        self.assertFalse(hunt.location_is_completed(0, 0, "wrong"))

    def test_distance_and_direction_heading_wraparound(self):
        """Test distance_and_direction handles heading > 360 degrees correctly."""
        # Create a location at a position that will cause heading wraparound
        location_wraparound = Location.objects.create(
            name="Wraparound Test",
            latitude=40.7128,
            longitude=-74.0060,
            clue="Test",
        )
        hunt = ScavengerHunt.objects.create(
            hunt_template=self.template,
            current_location=location_wraparound,
            location_ids=[location_wraparound.id],
        )
        # Position that creates a heading just west of north (should wrap around)
        distance, direction = hunt.distance_and_direction_to_current_location(
            40.7128, -74.007
        )
        self.assertGreater(distance, 0)
        # Direction should be valid (not throw an error from wraparound)
        self.assertIn(
            direction,
            [
                "north",
                "northeast",
                "east",
                "southeast",
                "south",
                "southwest",
                "west",
                "northwest",
            ],
        )


class ViewTests(TestCase):
    """Tests for scavenger hunt views."""

    @classmethod
    def setUpTestData(cls):
        # Create test locations
        cls.location1 = Location.objects.create(
            name="Location 1",
            latitude=40.7128,
            longitude=-74.0060,
            clue="Clue 1",
        )
        cls.location2 = Location.objects.create(
            name="Location 2",
            latitude=40.7589,
            longitude=-73.9851,
            clue="Clue 2",
            solutions=["answer"],
        )
        cls.location3 = Location.objects.create(
            name="Location 3 (no heading)",
            latitude=40.7489,
            longitude=-73.9680,
            clue="Clue 3",
            disable_heading=True,
        )
        # Create templates
        cls.template = ScavengerHuntTemplate.objects.create(
            name="Test Hunt",
            description="A test hunt",
            location_ids=[cls.location1.id, cls.location2.id],
        )
        cls.duplicate_template = ScavengerHuntTemplate.objects.create(
            name="Broken Hunt (duplicates)",
            location_ids=[cls.location1.id, cls.location1.id],
        )
        cls.invalid_location_template = ScavengerHuntTemplate.objects.create(
            name="Broken Hunt (invalid location)",
            location_ids=[99999],
        )

    def test_hunt_templates_view(self):
        """Test hunt_templates view returns all templates."""
        c = Client()
        response = c.get("/scavenger_hunt/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("hunt_templates", response.context)
        templates = response.context["hunt_templates"]
        self.assertGreaterEqual(len(templates), 3)

    def test_hunt_template_view(self):
        """Test hunt_template view returns template detail."""
        c = Client()
        response = c.get(f"/scavenger_hunt/{self.template.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["hunt_template"], self.template)

    def test_hunt_template_view_404(self):
        """Test hunt_template view returns 404 for invalid template."""
        c = Client()
        response = c.get("/scavenger_hunt/99999")
        self.assertEqual(response.status_code, 404)

    def test_create_new_hunt_success(self):
        """Test create_new_hunt creates a new hunt and redirects."""
        c = Client()
        response = c.post(f"/scavenger_hunt/{self.template.id}/instantiate")
        self.assertEqual(response.status_code, 302)
        # Verify hunt was created
        hunt = ScavengerHunt.objects.latest("created_at")
        self.assertEqual(hunt.hunt_template, self.template)
        self.assertEqual(hunt.current_location, self.location1)
        self.assertFalse(hunt.is_finished)

    def test_create_new_hunt_requires_post(self):
        """Test create_new_hunt only accepts POST."""
        c = Client()
        response = c.get(f"/scavenger_hunt/{self.template.id}/instantiate")
        self.assertEqual(response.status_code, 405)

    def test_create_new_hunt_with_duplicate_locations(self):
        """Test create_new_hunt fails with duplicate location IDs."""
        c = Client()
        response = c.post(f"/scavenger_hunt/{self.duplicate_template.id}/instantiate")
        self.assertEqual(response.status_code, 400)
        self.assertIn("duplicate location ids", response.reason_phrase)

    def test_create_new_hunt_with_invalid_location(self):
        """Test create_new_hunt fails with invalid location ID."""
        c = Client()
        response = c.post(
            f"/scavenger_hunt/{self.invalid_location_template.id}/instantiate"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("invalid next location", response.reason_phrase)

    def test_hunt_view_get(self):
        """Test hunt view GET returns hunt details."""
        hunt = ScavengerHunt.objects.create(
            hunt_template=self.template,
            current_location=self.location1,
            location_ids=[self.location1.id, self.location2.id],
        )
        c = Client()
        response = c.get(f"/scavenger_hunt/active/{hunt.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["hunt"], hunt)
        self.assertTrue(response.context["success"])
        self.assertFalse(response.context["first_time"])

    def test_hunt_view_get_with_params(self):
        """Test hunt view GET with query parameters."""
        hunt = ScavengerHunt.objects.create(
            hunt_template=self.template,
            current_location=self.location1,
            location_ids=[self.location1.id],
        )
        c = Client()
        response = c.get(
            f"/scavenger_hunt/active/{hunt.id}?success=False&firstTime=True"
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["success"])
        self.assertTrue(response.context["first_time"])

    def test_hunt_view_post_enter_post_location_phase(self):
        """Test hunt view POST successfully enters post_location_phase."""
        hunt = ScavengerHunt.objects.create(
            hunt_template=self.template,
            current_location=self.location1,
            location_ids=[self.location1.id, self.location2.id],
        )
        c = Client()
        # Post from very close to location
        response = c.post(
            f"/scavenger_hunt/active/{hunt.id}",
            {"latitude": "40.7128", "longitude": "-74.0060", "solution": ""},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("success=True", response.url)
        # Reload hunt from DB
        hunt.refresh_from_db()
        self.assertTrue(hunt.post_location_phase)

    def test_hunt_view_post_advance_to_next_location(self):
        """Test hunt view POST advances to next location from post_location_phase."""
        hunt = ScavengerHunt.objects.create(
            hunt_template=self.template,
            current_location=self.location1,
            location_ids=[self.location1.id, self.location2.id],
            post_location_phase=True,
        )
        c = Client()
        response = c.post(
            f"/scavenger_hunt/active/{hunt.id}",
            {"latitude": "0", "longitude": "0", "solution": ""},
        )
        self.assertEqual(response.status_code, 302)
        # Reload hunt from DB
        hunt.refresh_from_db()
        self.assertEqual(hunt.current_location, self.location2)
        self.assertFalse(hunt.post_location_phase)

    def test_hunt_view_post_finish_hunt(self):
        """Test hunt view POST finishes hunt when no more locations."""
        hunt = ScavengerHunt.objects.create(
            hunt_template=self.template,
            current_location=self.location2,
            location_ids=[self.location1.id, self.location2.id],
            post_location_phase=True,
        )
        c = Client()
        response = c.post(
            f"/scavenger_hunt/active/{hunt.id}",
            {"latitude": "0", "longitude": "0", "solution": ""},
        )
        self.assertEqual(response.status_code, 302)
        # Reload hunt from DB
        hunt.refresh_from_db()
        self.assertIsNone(hunt.current_location)
        self.assertTrue(hunt.is_finished)

    def test_hunt_view_post_failure(self):
        """Test hunt view POST redirects with success=False on failure."""
        hunt = ScavengerHunt.objects.create(
            hunt_template=self.template,
            current_location=self.location1,
            location_ids=[self.location1.id],
        )
        c = Client()
        # Post from far away
        response = c.post(
            f"/scavenger_hunt/active/{hunt.id}",
            {"latitude": "41.0", "longitude": "-75.0", "solution": ""},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("success=False", response.url)

    def test_hunt_view_post_corrupted_hunt_data(self):
        """Test hunt view POST returns error when hunt data is corrupted."""
        # Create a hunt with current_location not in location_ids
        hunt = ScavengerHunt.objects.create(
            hunt_template=self.template,
            current_location=self.location2,  # location2.id not in location_ids
            location_ids=[self.location1.id],
            post_location_phase=True,
        )
        c = Client()
        response = c.post(
            f"/scavenger_hunt/active/{hunt.id}",
            {"latitude": "0", "longitude": "0", "solution": ""},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("invalid current location", response.reason_phrase)

    def test_hunt_view_invalid_method(self):
        """Test hunt view rejects invalid HTTP methods."""
        hunt = ScavengerHunt.objects.create(
            hunt_template=self.template,
            current_location=self.location1,
            location_ids=[self.location1.id],
        )
        c = Client()
        response = c.put(f"/scavenger_hunt/active/{hunt.id}")
        self.assertEqual(response.status_code, 405)

    def test_hunt_heading_success(self):
        """Test hunt_heading returns correct JSON response."""
        hunt = ScavengerHunt.objects.create(
            hunt_template=self.template,
            current_location=self.location1,
            location_ids=[self.location1.id],
        )
        c = Client()
        response = c.get(
            f"/scavenger_hunt/active/{hunt.id}/heading",
            {"latitude": "40.70", "longitude": "-74.0060"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("distance", data)
        self.assertIn("direction", data)
        self.assertIn("required_distance", data)
        self.assertEqual(data["direction"], "north")

    def test_hunt_heading_requires_get(self):
        """Test hunt_heading only accepts GET."""
        hunt = ScavengerHunt.objects.create(
            hunt_template=self.template,
            current_location=self.location1,
            location_ids=[self.location1.id],
        )
        c = Client()
        response = c.post(f"/scavenger_hunt/active/{hunt.id}/heading")
        self.assertEqual(response.status_code, 405)

    def test_hunt_heading_invalid_params(self):
        """Test hunt_heading returns 400 for invalid parameters."""
        hunt = ScavengerHunt.objects.create(
            hunt_template=self.template,
            current_location=self.location1,
            location_ids=[self.location1.id],
        )
        c = Client()
        response = c.get(f"/scavenger_hunt/active/{hunt.id}/heading")
        self.assertEqual(response.status_code, 400)

    def test_hunt_heading_disabled(self):
        """Test hunt_heading returns 403 when heading is disabled."""
        hunt = ScavengerHunt.objects.create(
            hunt_template=self.template,
            current_location=self.location3,  # disable_heading=True
            location_ids=[self.location3.id],
        )
        c = Client()
        response = c.get(
            f"/scavenger_hunt/active/{hunt.id}/heading",
            {"latitude": "40.7128", "longitude": "-74.0060"},
        )
        self.assertEqual(response.status_code, 403)

    def test_hunt_heading_unknown_location(self):
        """Test hunt_heading returns 404 for location without coordinates."""
        location_no_coords = Location.objects.create(
            name="No Coords",
            clue="Test",
            solutions=["answer"],
        )
        hunt = ScavengerHunt.objects.create(
            hunt_template=self.template,
            current_location=location_no_coords,
            location_ids=[location_no_coords.id],
        )
        c = Client()
        response = c.get(
            f"/scavenger_hunt/active/{hunt.id}/heading",
            {"latitude": "40.7128", "longitude": "-74.0060"},
        )
        self.assertEqual(response.status_code, 404)
