"""Unit tests for music app models."""

import os
import tempfile
from datetime import datetime, timezone
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase

from .models import (
    BestOf,
    Comment,
    Music,
    Musician,
    Tag,
    convert_markdown_and_mark_safe,
    convert_name_to_directory_format,
)


class HelperFunctionTests(TestCase):
    """Tests for standalone helper functions in models.py."""

    def test_convert_name_to_directory_format_lowercase(self):
        """Test that names are converted to lowercase."""
        result = convert_name_to_directory_format("Test Band")
        self.assertEqual(result, "test_band")

    def test_convert_name_to_directory_format_replaces_spaces(self):
        """Test that spaces are replaced with underscores."""
        result = convert_name_to_directory_format("the rolling stones")
        self.assertEqual(result, "the_rolling_stones")

    def test_convert_name_to_directory_format_removes_special_chars(self):
        """Test that special characters are removed."""
        result = convert_name_to_directory_format("AC/DC!")
        self.assertEqual(result, "acdc")

    def test_convert_name_to_directory_format_preserves_alphanumeric(self):
        """Test that alphanumeric characters are preserved."""
        result = convert_name_to_directory_format("Blink 182")
        self.assertEqual(result, "blink_182")

    def test_convert_markdown_and_mark_safe_converts_markdown(self):
        """Test that markdown is converted to HTML."""
        result = convert_markdown_and_mark_safe("**bold**")
        self.assertIn("<strong>bold</strong>", str(result))

    def test_convert_markdown_and_mark_safe_handles_none(self):
        """Test that None input returns None."""
        result = convert_markdown_and_mark_safe(None)
        self.assertIsNone(result)


class MusicModelTests(TestCase):
    """Tests for Music model methods."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data for all tests in this class."""
        # Create tags
        cls.tag1 = Tag.objects.create(name="Death Metal")
        cls.tag2 = Tag.objects.create(name="Progressive Rock")

        # Create musician with tags
        cls.musician = Musician.objects.create(name="Test Band")
        cls.musician.tags.add(cls.tag1, cls.tag2)

        # Create album
        cls.album = Music.objects.create(
            name="Test Album",
            musician=cls.musician,
            rating=3,
            reviewed_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )

    def setUp(self):
        """Set up temporary directories for file tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_base_dir = settings.BASE_DIR

    def tearDown(self):
        """Clean up temporary files."""
        # Clean up temp directory
        for root, dirs, files in os.walk(self.temp_dir, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(self.temp_dir)

    def test_music_str_representation(self):
        """Test that __str__ returns musician and album name."""
        expected = "Test Band: Test Album"
        self.assertEqual(str(self.album), expected)

    def test_review_txt_reads_file(self):
        """Test that review_txt reads markdown from file."""
        # Create test review file
        review_dir = os.path.join(self.temp_dir, "music/reviews/test_band")
        os.makedirs(review_dir, exist_ok=True)
        review_path = os.path.join(review_dir, "test_album.md")

        with open(review_path, "w", encoding="utf-8") as f:
            f.write("# Test Review\n\nThis is a test review.")

        with patch.object(settings, "BASE_DIR", self.temp_dir):
            result = self.album.review_txt()
            self.assertEqual(result, "# Test Review\n\nThis is a test review.")

    def test_review_txt_with_missing_file(self):
        """Test that review_txt returns None when file doesn't exist."""
        with patch.object(settings, "BASE_DIR", self.temp_dir):
            result = self.album.review_txt()
            self.assertIsNone(result)

    def test_review_with_existing_file(self):
        """Test that review converts markdown to HTML."""
        # Create test review file
        review_dir = os.path.join(self.temp_dir, "music/reviews/test_band")
        os.makedirs(review_dir, exist_ok=True)
        review_path = os.path.join(review_dir, "test_album.md")

        with open(review_path, "w", encoding="utf-8") as f:
            f.write("**Bold text**")

        with patch.object(settings, "BASE_DIR", self.temp_dir):
            result = self.album.review()
            self.assertIn("<strong>Bold text</strong>", str(result))

    def test_review_with_missing_file(self):
        """Test that review returns None when file doesn't exist."""
        with patch.object(settings, "BASE_DIR", self.temp_dir):
            result = self.album.review()
            self.assertIsNone(result)

    def test_description_with_tags(self):
        """Test that description includes tag list."""
        result = self.album.description()
        self.assertIn("(Death Metal, Progressive Rock)", result)

    def test_description_without_tags(self):
        """Test that description shows '[no tags]' when no tags exist."""
        # Create album with musician that has no tags
        musician_no_tags = Musician.objects.create(name="No Tags Band")
        album_no_tags = Music.objects.create(
            name="No Tags Album",
            musician=musician_no_tags,
            rating=2,
            reviewed_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )

        result = album_no_tags.description()
        self.assertIn("[no tags]", result)

    def test_description_with_no_review(self):
        """Test that description shows '[no review]' when no review file exists."""
        with patch.object(settings, "BASE_DIR", self.temp_dir):
            result = self.album.description()
            self.assertIn("[no review]", result)

    def test_description_clips_long_reviews(self):
        """Test that description clips reviews to 500 characters."""
        # Create a long review
        long_review = "x" * 600
        review_dir = os.path.join(self.temp_dir, "music/reviews/test_band")
        os.makedirs(review_dir, exist_ok=True)
        review_path = os.path.join(review_dir, "test_album.md")

        with open(review_path, "w", encoding="utf-8") as f:
            f.write(long_review)

        with patch.object(settings, "BASE_DIR", self.temp_dir):
            result = self.album.description()
            # Should have tags, space, 500 chars, and "..."
            self.assertTrue(result.endswith("..."))
            # Count only the review portion (after tags)
            review_portion = result.split(") ")[1]
            self.assertEqual(len(review_portion), 503)  # 500 + "..."

    def test_image_src_exists(self):
        """Test that image_src returns path when image exists."""
        # Create test image file
        image_dir = os.path.join(self.temp_dir, "music/static/music/images/test_band")
        os.makedirs(image_dir, exist_ok=True)
        image_path = os.path.join(image_dir, "test_album.jpg")

        with open(image_path, "w") as f:
            f.write("fake image")

        with patch.object(settings, "BASE_DIR", self.temp_dir):
            result = self.album.image_src()
            expected = "music/images/test_band/test_album.jpg"
            self.assertEqual(result, expected)

    def test_image_src_missing(self):
        """Test that image_src returns None when image doesn't exist."""
        with patch.object(settings, "BASE_DIR", self.temp_dir):
            result = self.album.image_src()
            self.assertIsNone(result)

    def test_classes_returns_tag_classnames(self):
        """Test that classes returns list of CSS class names from tags."""
        result = self.album.classes()
        self.assertEqual(result, ["DeathMetal", "ProgressiveRock"])


class MusicianModelTests(TestCase):
    """Tests for Musician model."""

    def test_musician_str_representation(self):
        """Test that __str__ returns the musician name."""
        musician = Musician.objects.create(name="The Beatles")
        self.assertEqual(str(musician), "The Beatles")


class TagModelTests(TestCase):
    """Tests for Tag model."""

    def test_tag_str_representation(self):
        """Test that __str__ returns the tag name."""
        tag = Tag.objects.create(name="Jazz")
        self.assertEqual(str(tag), "Jazz")

    def test_classname_removes_spaces(self):
        """Test that classname removes spaces for CSS classes."""
        tag = Tag.objects.create(name="Death Metal")
        self.assertEqual(tag.classname(), "DeathMetal")


class CommentModelTests(TestCase):
    """Tests for Comment model."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data for all tests in this class."""
        cls.user = User.objects.create_user(
            username="testuser",
            first_name="John",
            last_name="Doe",
            email="test@example.com",
            password="testpass123",
        )
        cls.user_no_name = User.objects.create_user(
            username="anonymous", email="anon@example.com", password="testpass123"
        )
        cls.musician = Musician.objects.create(name="Test Band")
        cls.album = Music.objects.create(
            name="Test Album",
            musician=cls.musician,
            rating=3,
            reviewed_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )

    def test_comment_str_representation(self):
        """Test that __str__ returns formatted string with id and username."""
        comment = Comment.objects.create(
            text="Great album!", author=self.user, album=self.album
        )
        expected = f"#{comment.id}, author=testuser"
        self.assertEqual(str(comment), expected)

    def test_display_name_with_full_name(self):
        """Test that display_name formats as 'First L.' when full name available."""
        comment = Comment.objects.create(
            text="Great album!", author=self.user, album=self.album
        )
        self.assertEqual(comment.display_name, "John D.")

    def test_display_name_username_only(self):
        """Test that display_name falls back to username when no full name."""
        comment = Comment.objects.create(
            text="Good stuff", author=self.user_no_name, album=self.album
        )
        self.assertEqual(comment.display_name, "anonymous")


class BestOfModelTests(TestCase):
    """Tests for BestOf model."""

    def setUp(self):
        """Set up temporary directories for file tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.best_of = BestOf.objects.create(
            name="Best of 2023",
            start_date=datetime(2023, 1, 1).date(),
            end_date=datetime(2023, 12, 31).date(),
        )

    def tearDown(self):
        """Clean up temporary files."""
        for root, dirs, files in os.walk(self.temp_dir, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(self.temp_dir)

    def test_bestof_str_representation(self):
        """Test that __str__ returns formatted string with name and dates."""
        expected = "Best of 2023: 2023-01-01 until 2023-12-31"
        self.assertEqual(str(self.best_of), expected)

    def test_description_txt_reads_file(self):
        """Test that description_txt reads markdown from file."""
        # Create test description file
        desc_dir = os.path.join(self.temp_dir, "music/best_of")
        os.makedirs(desc_dir, exist_ok=True)
        desc_path = os.path.join(desc_dir, "best_of_2023.md")

        with open(desc_path, "w", encoding="utf-8") as f:
            f.write("# Best Albums of 2023\n\nAn amazing year!")

        with patch.object(settings, "BASE_DIR", self.temp_dir):
            result = self.best_of.description_txt()
            self.assertEqual(result, "# Best Albums of 2023\n\nAn amazing year!")

    def test_description_txt_with_missing_file(self):
        """Test that description_txt returns None when file doesn't exist."""
        with patch.object(settings, "BASE_DIR", self.temp_dir):
            result = self.best_of.description_txt()
            self.assertIsNone(result)

    def test_description_converts_markdown(self):
        """Test that description converts markdown to HTML."""
        # Create test description file
        desc_dir = os.path.join(self.temp_dir, "music/best_of")
        os.makedirs(desc_dir, exist_ok=True)
        desc_path = os.path.join(desc_dir, "best_of_2023.md")

        with open(desc_path, "w", encoding="utf-8") as f:
            f.write("**Bold text**")

        with patch.object(settings, "BASE_DIR", self.temp_dir):
            result = self.best_of.description()
            self.assertIn("<strong>Bold text</strong>", str(result))

    def test_description_with_missing_file(self):
        """Test that description returns None when file doesn't exist."""
        with patch.object(settings, "BASE_DIR", self.temp_dir):
            result = self.best_of.description()
            self.assertIsNone(result)
