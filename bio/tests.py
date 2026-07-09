from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse


class BioViewTests(TestCase):
    def test_root_url_returns_200_and_uses_bio_template(self) -> None:
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "bio/bio.html")

    def test_home_url_name_reverses_to_root(self) -> None:
        self.assertEqual(reverse("home"), "/")

    def test_bio_markdown_rendered_as_html_links(self) -> None:
        response = self.client.get("/")
        self.assertContains(
            response, '<a href="https://en.wikipedia.org/wiki/Loon_LLC">'
        )
        self.assertContains(
            response, "https://www.linkedin.com/in/paul-carroll-b38592a6/"
        )
        self.assertContains(response, "https://github.com/vpcarroll15")
        self.assertContains(response, "https://paulcarroll.site/music/")

    def test_bio_markdown_file_missing_returns_404(self) -> None:
        with patch("bio.views.BIO_MARKDOWN_PATH", "bio/does_not_exist.md"):
            response = self.client.get("/")
        self.assertEqual(response.status_code, 404)
