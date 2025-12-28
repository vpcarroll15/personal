"""Unit tests for music app views and helper functions."""

from datetime import datetime, timezone

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import BestOf, Comment, Music, Musician, Tag
from .views import (
    apply_common_preselects_music,
    get_recent_music,
    update_context_with_album,
)


class HelperFunctionTests(TestCase):
    """Tests for view helper functions."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data for all tests in this class."""
        # Create tags
        cls.tag1 = Tag.objects.create(name="Jazz")
        cls.tag2 = Tag.objects.create(name="Blues")

        # Create musician
        cls.musician = Musician.objects.create(name="Miles Davis")
        cls.musician.tags.add(cls.tag1, cls.tag2)

        # Create test user
        cls.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        # Create albums
        cls.album1 = Music.objects.create(
            name="Kind of Blue",
            musician=cls.musician,
            rating=3,
            reviewed_at=datetime(2024, 1, 15, tzinfo=timezone.utc),
        )
        cls.album2 = Music.objects.create(
            name="Sketches of Spain",
            musician=cls.musician,
            rating=2,
            reviewed_at=datetime(2024, 1, 10, tzinfo=timezone.utc),
        )
        cls.album3 = Music.objects.create(
            name="Bitches Brew",
            musician=cls.musician,
            rating=3,
            reviewed_at=datetime(2024, 1, 5, tzinfo=timezone.utc),
        )

        # Create comment
        cls.comment1 = Comment.objects.create(
            text="Great album!", author=cls.user, album=cls.album1
        )

    def test_update_context_with_album_adds_album(self):
        """Test that update_context_with_album adds album to context."""
        context = {}
        update_context_with_album(context, self.album1)
        self.assertEqual(context["album"], self.album1)

    def test_update_context_with_album_includes_tags(self):
        """Test that update_context_with_album includes tags."""
        context = {}
        update_context_with_album(context, self.album1)
        tags = list(context["tags"])
        self.assertIn(self.tag1, tags)
        self.assertIn(self.tag2, tags)

    def test_update_context_with_album_includes_comments_when_enabled(self):
        """Test that comments are included when show_comments=True."""
        context = {}
        update_context_with_album(context, self.album1, show_comments=True)
        self.assertTrue(context["show_comments"])
        self.assertIn("comments", context)
        comments = list(context["comments"])
        self.assertIn(self.comment1, comments)

    def test_update_context_with_album_excludes_comments_when_disabled(self):
        """Test that comments are excluded when show_comments=False."""
        context = {}
        update_context_with_album(context, self.album1, show_comments=False)
        self.assertFalse(context["show_comments"])
        self.assertNotIn("comments", context)

    def test_apply_common_preselects_music_applies_optimizations(self):
        """Test that apply_common_preselects_music applies select/prefetch_related."""
        queryset = Music.objects.all()
        result = apply_common_preselects_music(queryset)

        # Check that the queryset has the expected optimizations
        # This is indicated by the presence of _prefetch_related_lookups and select_related
        self.assertTrue(hasattr(result, "_prefetch_related_lookups"))
        self.assertIn("musician__tags", result._prefetch_related_lookups)
        self.assertIn("comment_set", result._prefetch_related_lookups)

    def test_get_recent_music_returns_correct_quantity(self):
        """Test that get_recent_music returns the requested number of albums."""
        result = get_recent_music(quantity=2)
        self.assertEqual(len(result), 2)

    def test_get_recent_music_orders_by_reviewed_at_desc(self):
        """Test that get_recent_music orders by reviewed_at in descending order."""
        result = list(get_recent_music(quantity=3))
        # Should be in reverse chronological order
        self.assertEqual(result[0], self.album1)  # Jan 15
        self.assertEqual(result[1], self.album2)  # Jan 10
        self.assertEqual(result[2], self.album3)  # Jan 5

    def test_get_recent_music_default_quantity(self):
        """Test that get_recent_music uses default quantity of 10."""
        result = get_recent_music()
        # We only have 3 albums, so should return all 3
        self.assertEqual(len(result), 3)


class CommentViewTests(TestCase):
    """Tests for the comment() view."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data for all tests in this class."""
        cls.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        cls.musician = Musician.objects.create(name="Test Band")
        cls.album = Music.objects.create(
            name="Test Album",
            musician=cls.musician,
            rating=3,
            reviewed_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )

    def test_comment_requires_login(self):
        """Test that comment view requires authentication."""
        response = self.client.post(
            reverse("music:comment", args=[self.album.id]),
            {"comment": "Test comment"},
        )
        # Should redirect to login page
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_comment_creates_comment_object(self):
        """Test that comment view creates a comment in the database."""
        self.client.force_login(self.user)
        initial_count = Comment.objects.count()

        response = self.client.post(
            reverse("music:comment", args=[self.album.id]),
            {"comment": "Great album!"},
        )

        # Should create a new comment
        self.assertEqual(Comment.objects.count(), initial_count + 1)
        new_comment = Comment.objects.latest("created_at")
        self.assertEqual(new_comment.text, "Great album!")
        self.assertEqual(new_comment.author, self.user)
        self.assertEqual(new_comment.album, self.album)

    def test_comment_rejects_get_requests(self):
        """Test that comment view only accepts POST requests."""
        self.client.force_login(self.user)
        response = self.client.get(reverse("music:comment", args=[self.album.id]))
        self.assertEqual(response.status_code, 405)  # Method Not Allowed

    def test_comment_handles_missing_data(self):
        """Test that comment view returns 400 when POST data is missing."""
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("music:comment", args=[self.album.id]),
            {},  # No comment field
        )
        self.assertEqual(response.status_code, 400)

    def test_comment_redirects_to_album_page(self):
        """Test that comment view redirects to the album detail page."""
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("music:comment", args=[self.album.id]),
            {"comment": "Test comment"},
        )
        expected_url = reverse(
            "music:music_detailed", kwargs={"music_id": self.album.id}
        )
        self.assertRedirects(response, expected_url, fetch_redirect_response=False)


class BestOfViewTests(TestCase):
    """Tests for the best_of() view."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data for all tests in this class."""
        # Create tags
        cls.tag_rock = Tag.objects.create(name="Rock")
        cls.tag_metal = Tag.objects.create(name="Metal")

        # Create musicians
        cls.musician1 = Musician.objects.create(name="Band One")
        cls.musician1.tags.add(cls.tag_rock)
        cls.musician2 = Musician.objects.create(name="Band Two")
        cls.musician2.tags.add(cls.tag_metal)

        # Create BestOf period
        # Note: view uses __gt and __lt (strict comparisons), so we need to set
        # start_date before the earliest album and end_date after the latest
        cls.best_of_2023 = BestOf.objects.create(
            name="2023",
            start_date=datetime(2022, 12, 31).date(),  # Day before earliest album
            end_date=datetime(2023, 12, 31).date(),  # Day after latest album
        )

        # Create albums within the period with different ratings
        cls.best_album = Music.objects.create(
            name="Best Album",
            musician=cls.musician1,
            rating=3,
            reviewed_at=datetime(2023, 6, 15, tzinfo=timezone.utc),
        )
        cls.great_album = Music.objects.create(
            name="Great Album",
            musician=cls.musician1,
            rating=2,
            reviewed_at=datetime(2023, 5, 10, tzinfo=timezone.utc),
        )
        cls.good_album = Music.objects.create(
            name="Good Album",
            musician=cls.musician2,
            rating=1,
            reviewed_at=datetime(2023, 8, 20, tzinfo=timezone.utc),
        )

        # Create album outside the period (should be excluded)
        cls.album_outside_period = Music.objects.create(
            name="Outside Period",
            musician=cls.musician1,
            rating=3,
            reviewed_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )

        # Create album that should be excluded
        cls.excluded_album = Music.objects.create(
            name="Excluded Album",
            musician=cls.musician1,
            rating=3,
            reviewed_at=datetime(2023, 7, 1, tzinfo=timezone.utc),
            exclude_from_best_of_list=True,
        )

    def test_best_of_filters_by_date_range(self):
        """Test that best_of view filters albums by date range."""
        response = self.client.get(reverse("music:best_of", args=["2023"]))
        self.assertEqual(response.status_code, 200)

        # Get all albums in the response context
        all_albums = (
            list(response.context["best_albums"])
            + list(response.context["great_albums"])
            + list(response.context["good_albums"])
        )

        # Should not include album outside the period
        self.assertNotIn(self.album_outside_period, all_albums)

    def test_best_of_excludes_flagged_albums(self):
        """Test that albums with exclude_from_best_of_list=True are excluded."""
        response = self.client.get(reverse("music:best_of", args=["2023"]))
        self.assertEqual(response.status_code, 200)

        all_albums = (
            list(response.context["best_albums"])
            + list(response.context["great_albums"])
            + list(response.context["good_albums"])
        )

        # Should not include excluded album
        self.assertNotIn(self.excluded_album, all_albums)

    def test_best_of_partitions_by_rating(self):
        """Test that albums are partitioned by rating (albums_by_score)."""
        response = self.client.get(reverse("music:best_of", args=["2023"]))
        self.assertEqual(response.status_code, 200)

        # Check that albums are in correct rating categories
        self.assertIn(self.best_album, response.context["best_albums"])
        self.assertIn(self.great_album, response.context["great_albums"])
        self.assertIn(self.good_album, response.context["good_albums"])

    def test_best_of_sorts_by_reviewed_at(self):
        """Test that albums within each rating are sorted by reviewed_at."""
        # Create more albums with same rating to test sorting
        album1 = Music.objects.create(
            name="Earlier",
            musician=self.musician1,
            rating=3,
            reviewed_at=datetime(2023, 3, 1, tzinfo=timezone.utc),
        )
        album2 = Music.objects.create(
            name="Later",
            musician=self.musician1,
            rating=3,
            reviewed_at=datetime(2023, 9, 1, tzinfo=timezone.utc),
        )

        response = self.client.get(reverse("music:best_of", args=["2023"]))
        best_albums = list(response.context["best_albums"])

        # Should be sorted chronologically (earliest first)
        self.assertEqual(best_albums[0], album1)
        # album2 should come after album1
        self.assertTrue(best_albums.index(album2) > best_albums.index(album1))

    def test_best_of_includes_tags_with_quantity(self):
        """Test that tags are counted and included in context."""
        response = self.client.get(reverse("music:best_of", args=["2023"]))
        self.assertEqual(response.status_code, 200)

        # Verify that tags_with_quantity exists in context
        self.assertIn("tags_with_quantity", response.context)
        tags_with_quantity = list(response.context["tags_with_quantity"])

        # Verify it's a list of (tag, count) tuples
        self.assertIsInstance(tags_with_quantity, list)
        if tags_with_quantity:  # If there are any tags
            tag, count = tags_with_quantity[0]
            self.assertIsInstance(count, int)
            self.assertGreater(count, 0)

    def test_best_of_404_on_invalid_name(self):
        """Test that best_of returns 404 for non-existent BestOf name."""
        response = self.client.get(reverse("music:best_of", args=["nonexistent"]))
        self.assertEqual(response.status_code, 404)


class SearchViewTests(TestCase):
    """Additional tests for the search() view beyond integration tests."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data for all tests in this class."""
        cls.tag_jazz = Tag.objects.create(name="Jazz")
        cls.musician = Musician.objects.create(name="Miles Davis")
        cls.musician.tags.add(cls.tag_jazz)
        cls.album = Music.objects.create(
            name="Kind of Blue",
            musician=cls.musician,
            rating=3,
            reviewed_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )

    def test_search_by_album_name(self):
        """Test searching by album name."""
        response = self.client.get(reverse("music:search"), {"search_term": "Kind"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.album, response.context["albums"])

    def test_search_by_musician_name(self):
        """Test searching by musician name."""
        response = self.client.get(reverse("music:search"), {"search_term": "Miles"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.album, response.context["albums"])

    def test_search_by_tag(self):
        """Test searching by exact tag name."""
        response = self.client.get(reverse("music:search"), {"search_term": "Jazz"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.album, response.context["albums"])

    def test_search_case_insensitive(self):
        """Test that search is case insensitive."""
        response = self.client.get(reverse("music:search"), {"search_term": "MILES"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.album, response.context["albums"])
