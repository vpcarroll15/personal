from datetime import datetime, timedelta
import itertools
import random
import re
from typing import Dict, Iterator

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
import markdown2
import numpy


class SnippetType(models.TextChoices):
    GRATITUDE = "1", "GRATITUDE"
    REQUEST = "2", "REQUEST"
    PRAISE = "3", "PRAISE"


class PrayerSchema(models.Model):
    """
    The schema that we use to generate a prayer.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
    )
    name = models.TextField(help_text="The name of the prayer.")

    next_generation_time = models.DateTimeField(default=datetime.min, blank=True)
    generation_cadence = models.DurationField(default=timedelta(days=1), blank=True)
    generation_variance = models.DurationField(default=timedelta(hours=6), blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    schema = models.TextField(
        help_text=(
            "The schema that we use to generate the prayer. "
            "The schema consists of Markdown with special markers in it to indicate where we should insert "
            "a prayer snippet. Write: {{ GRATITUDE, 3 }} to indicate that "
            "we should indicate three gratitude snippets. You must follow this syntax exactly of "
            "snippet type, comma, number of snippets. Otherwise a ValueError will be raised when we try to "
            "save the schema."
        )
    )

    def should_generate(self):
        return self.next_generation_time <= datetime.now()

    def update_next_generation_time(self):
        """Update the time that we next generate the model."""
        seconds_of_variance = numpy.random.normal(0, self.generation_variance.total_seconds())
        self.next_generation_time = datetime.now() + self.generation_cadence + timedelta(seconds=seconds_of_variance)
        self.save()
    
    def get_snippets_by_type(self, use_sentinels=False) -> Dict[SnippetType, Iterator[str]]:
        # Next, retrieve all the snippets for this user if we aren't using sentinels.
        # If we are using sentinels, supply a convincing iterator instead.
        snippet_type_to_snippet: Dict[SnippetType, Iterator[str]] = {}

        for snippet_type in SnippetType:
            if use_sentinels:
                snippet_type_to_snippet[snippet_type] = itertools.repeat(f"{snippet_type.name}_SNIPPET_HERE")
            else:
                # We can resolve the whole list because it should be small.
                snippets = list(PrayerSnippet.objects.filter(
                    user=self.user,
                    type=snippet_type,
                    expires_at__gt=datetime.now(),
                ))
                # Sort. Make sure that the highest-weighted snippets go first.
                snippets.sort(key=lambda x: x.sample(), reverse=True)
                # Now convert each snippet into text.
                snippets_text = [snippet.text for snippet in snippets]
                snippet_type_to_snippet[snippet_type] = iter(snippets_text)

        return snippet_type_to_snippet

    def parse(self, use_sentinels=False):
        """
        Parse the schema and return the HTML prayer that we should send as an email.

        If use_sentinels=True, then we use placeholders like GRATITUDE_SNIPPET_HERE, REQUEST_SNIPPET_HERE
        instead of actually fetching the text of the snippet. This is useful for validating the schema
        when we save it.
        """
        # The first step is to parse the markdown and see if that works.
        parsed_schema = markdown2.markdown(self.schema)
        snippets_by_type = self.get_snippets_by_type(use_sentinels=use_sentinels)

        # This regex will turn strings like this:
        # "Start with this: {{ test }} and then this {{ test2, 3 }} finally"
        # into:
        # ['Start with this: ', '{{ test }}', ' and then this ', '{{ test2, 3 }}', ' finally']
        # From here, it is easy to parse and reassemble the output string.
        regex = r'({{.*?}})'
        split_schema = re.split(regex, parsed_schema)
        
        reassembled_schema = ''
        for elem in split_schema:
            if elem.startswith('{{') and elem.endswith('}}'):
                # This is a snippet, so we need to parse it.
                try:
                    snippet_type, snippet_count = elem[2:-2].split(',')
                    snippet_type = SnippetType[snippet_type.strip()]
                    snippet_count = int(snippet_count.strip())
                except Exception:
                    raise ValueError(f"Failed to parse snippet type or count from {elem}")
                
                # If the user just wants a single element, we use a paragraph instead of an
                # unordered list. This is just a nice display detail.
                if snippet_count == 1:
                    begin, end, element_begin, element_end = "<p>", "</p>", "", ""
                else:
                    begin, end, element_begin, element_end = "<ul>", "</ul>", "<li>", "</li>"
                
                snippet_html = begin
                for _ in range(snippet_count):
                    try:
                        snippet_html += element_begin + next(snippets_by_type[snippet_type]) + element_end
                    except StopIteration:
                        # If we are out of snippets, just keep going and insert nothing. There is nothing else
                        # we can do.
                        continue
                snippet_html += end
                reassembled_schema += snippet_html
            else:
                reassembled_schema += elem
        return reassembled_schema

    def save(self, *args, **kwargs):
        """
        Validate the schema before saving it.
        """
        self.parse(use_sentinels=True)
        super().save(*args, **kwargs)


class PrayerSnippet(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
    )

    text = models.TextField(help_text="The content of the snippet, which becomes part of the prayer.")
    type = models.CharField(
        max_length=20,
        choices=SnippetType.choices,
        help_text="The type of snippet."
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this snippet expires."
    )
    weighting = models.SmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        default=1,
        blank=True,
        help_text="The value of this snippet from 1 to 10.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def sample(self):
        """Sample the snippet according to its weighting and return a score from 0 to 1."""
        return max(random.random() for _ in range(self.weighting))
