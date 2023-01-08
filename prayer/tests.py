from datetime import datetime, timedelta, timezone

from django.core import mail
from django.test import TestCase
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from freezegun import freeze_time
from rest_framework.test import APITestCase

from prayer.models import PrayerSchema, PrayerSnippet, SnippetType


DATETIME_NOW = datetime(2022, 1, 30, 12, 0, 0, tzinfo=timezone.utc)


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
        self.assertEquals(without_sentinels, '<p><em>I am grateful for this.</em> I am snippet 6 of type GRATITUDE for user paul. I want this: <ul><li>I am snippet 6 of type REQUEST for user paul.</li><li>I am snippet 5 of type REQUEST for user paul.</li></ul></p>')

    def test_render_broken_snippets_fails(self):
        # This works.
        PrayerSchema.objects.create(
            user=self.user1,
            name="works",
            schema="{{ GRATITUDE, 1 }}",
        )
        with self.assertRaises(ValidationError):
            PrayerSchema.objects.create(
                user=self.user1,
                name="broken",
                schema="{{ GRATITUDE, NOTANUMBER }}",
            )
        with self.assertRaises(ValidationError):
            PrayerSchema.objects.create(
                user=self.user1,
                name="broken",
                schema="{{ NOTATHING, 1 }}",
            )
        with self.assertRaises(ValidationError):
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


@freeze_time(DATETIME_NOW)
class EmailTriggererTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create_user("paul", "paul@carroll.com", "paulpassword")
        cls.schema = PrayerSchema.objects.create(
            user=cls.user1,
            name="testname",
            schema="No snippets here.",
        )

        cls.triggerer = User.objects.create_user(
            "triggerer", "triggerer@carroll.com", "triggererpassword"
        )
        triggerer_group, _ = Group.objects.get_or_create(name="EmailTriggerer")
        triggerer_group.user_set.add(cls.triggerer)

    def test_email_triggerer(self):
        self.client.force_authenticate(user=self.triggerer)
        response = self.client.post("/prayer/trigger/", {})
        self.assertEqual(response.status_code, 200)
        updated_schema = PrayerSchema.objects.get(pk=self.schema.pk)
        assert updated_schema.next_generation_time == DATETIME_NOW + timedelta(days=1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["paul@carroll.com"])

        # Now try again and verify that we don't produce an email
        response = self.client.post("/prayer/trigger/", {})
        self.assertEqual(len(mail.outbox), 1)

    def test_wrong_credentials(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.post("/prayer/trigger/", {})
        self.assertEqual(response.status_code, 403)
