from datetime import datetime, timedelta
import random

from django.test import TestCase
from django.contrib.auth.models import User
from freezegun import freeze_time

from prayer.models import PrayerSchema, PrayerSnippet, SnippetType


DATETIME_NOW = datetime(2022, 1, 30, 12, 0, 0)


@freeze_time(DATETIME_NOW)
class PrayerSchemaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create_user("paul", "paul@carroll.com", "paulpassword")

        cls.user2 = User.objects.create_user(
            "grace", "grace@boorstein.com", "gracepassword"
        )

        for user in [cls.user1, cls.user2]:
            for snippet_type in SnippetType:
                for i in range(10):
                    PrayerSnippet.objects.create(
                        user=user,
                        text=f"I am snippet {i} of type {snippet_type.name} for user {user.username}.",
                        type=snippet_type,
                        fixed_weight = i / 10,
                        # Make sure that a few snippets are expired.
                        expires_at=DATETIME_NOW + timedelta(days=7 - i),
                    )
    
    def test_render_no_snippets(self):
        schema = PrayerSchema.objects.create(
            user=self.user1,
            name="testname",
            schema="No snippets here.",
        )
        with_sentinels = schema.render(use_sentinels=True)
        without_sentinels = schema.render(use_sentinels=False)
        self.assertEquals(with_sentinels, "<p>No snippets here.</p>")
        self.assertEquals(without_sentinels, "<p>No snippets here.</p>")

    def test_render_with_snippets(self):
        schema = PrayerSchema.objects.create(
            user=self.user1,
            name="testname",
            schema="*I am grateful for this.* {{ GRATITUDE, 1 }} I want this: {{ REQUEST, 2 }}",
        )
        with_sentinels = schema.render(use_sentinels=True)
        without_sentinels = schema.render(use_sentinels=False)
        self.assertEquals(with_sentinels, '<p><em>I am grateful for this.</em> GRATITUDE_SNIPPET_HERE I want this: <ul><li>REQUEST_SNIPPET_HERE</li><li>REQUEST_SNIPPET_HERE</li></ul></p>')
        self.assertEquals(without_sentinels, '<p><em>I am grateful for this.</em> I am snippet 7 of type GRATITUDE for user paul. I want this: <ul><li>I am snippet 7 of type REQUEST for user paul.</li><li>I am snippet 6 of type REQUEST for user paul.</li></ul></p>')

    def test_render_broken_snippets_fails(self):
        # This works.
        PrayerSchema.objects.create(
            user=self.user1,
            name="works",
            schema="{{ GRATITUDE, 1 }}",
        )
        with self.assertRaises(ValueError):
            PrayerSchema.objects.create(
                user=self.user1,
                name="broken",
                schema="{{ GRATITUDE, NOTANUMBER }}",
            )
        with self.assertRaises(ValueError):
            PrayerSchema.objects.create(
                user=self.user1,
                name="broken",
                schema="{{ NOTATHING, 1 }}",
            )
        with self.assertRaises(ValueError):
            PrayerSchema.objects.create(
                user=self.user1,
                name="broken",
                schema="{{ GRATITUDE }}",
            )

    def test_many_snippets_exhausts(self):
        schema = PrayerSchema.objects.create(
            user=self.user1,
            name="works",
            schema="{{ GRATITUDE, 1000 }}",
        )
        # Just check that this doesn't throw an error.
        schema.render(use_sentinels=False)
 
    def test_render_escaped_html(self):
        PrayerSnippet.objects.create(
            user=self.user1,
            text=f"<h1>Escape this!</h1>",
            type="GRATITUDE",
            fixed_weight=1.0,
        )
        schema = PrayerSchema.objects.create(
            user=self.user1,
            name="testname",
            schema="{{ GRATITUDE, 1 }}",
        )
        without_sentinels = schema.render(use_sentinels=False)
        self.assertEquals(without_sentinels, '<p>&lt;h1&gt;Escape this!&lt;/h1&gt;</p>')

    def test_generation_time(self):
        schema = PrayerSchema.objects.create(
            user=self.user1,
            name="testname",
            schema="{{ GRATITUDE, 1 }}",
        )
        assert schema.next_generation_time == DATETIME_NOW
        assert schema.should_generate()
        schema.update_next_generation_time()
        assert schema.next_generation_time == DATETIME_NOW + timedelta(days=1)
