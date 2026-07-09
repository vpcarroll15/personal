import os

import markdown2
from django.conf import settings
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils.safestring import mark_safe

# Constants
BIO_MARKDOWN_PATH = "bio/bio.md"


def bio(request: HttpRequest) -> HttpResponse:
    """Renders the bio markdown file as the site's landing page."""
    path_to_bio = os.path.join(settings.BASE_DIR, BIO_MARKDOWN_PATH)
    try:
        with open(path_to_bio, encoding="utf-8") as bio_file:
            bio_as_markdown = bio_file.read()
    except IOError as exc:
        raise Http404("Bio content not found.") from exc

    bio_as_html = markdown2.markdown(bio_as_markdown)
    # Safe to render as HTML because I write the markdown myself.
    context = {"bio_html": mark_safe(bio_as_html)}
    return render(request, "bio/bio.html", context)
