"""
An integration test that is designed to validate that we can query for a bunch of albums without returning an error
code other than 200.

From time to time, the fixture will need to be updated in order to test against new model fields. To do this, you can
use the Django dumpdata tool.
"""

from django.test import TestCase
from django.urls import reverse

from .models import Music


class IntegrationTestCase(TestCase):
    fixtures = ["db_contents_06032019.json"]

    def test_music_detailed(self):
        """Make sure that we can render a view for each of the albums."""
        num_albums = Music.objects.count()

        for i in range(num_albums):
            response = self.client.get(reverse("music:music_detailed", args=[i + 1]))
            self.assertEqual(response.status_code, 200)

    def test_search(self):
        """Make sure that we can render a view for some basic search terms."""
        search_terms = ["", "Aphex Twin", "metal", "Land of the Dead"]

        for search_term in search_terms:
            response = self.client.get(
                reverse("music:search"), {"search_term": search_term}
            )
            self.assertEqual(response.status_code, 200)

    def test_ratings(self):
        """Make sure that we can render a view for the ratings page."""
        response = self.client.get(reverse("music:ratings"))
        self.assertEqual(response.status_code, 200)

    def test_rss(self):
        """Make sure that we can render a view for the rss feed."""
        response = self.client.get(reverse("music:rss"))
        self.assertEqual(response.status_code, 200)

    def test_home(self):
        """Make sure that we can render a view for the home page."""
        response = self.client.get(reverse("music:home"))
        self.assertEqual(response.status_code, 200)
