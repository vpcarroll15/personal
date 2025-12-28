from datetime import datetime, timedelta, timezone

import pytz
from django.contrib.auth.models import Group, User
from django.test import Client, TestCase
from rest_framework.test import APITestCase

from prayer.models import PrayerSnippet
from sms.models import DataPoint, Question
from sms.models import User as SmsUser


class AccountTests(APITestCase):
    def setUp(self):
        webhooker = User.objects.create_user(
            "webhooker", "paul@carroll.com", "paulpassword"
        )
        webhook_group, _ = Group.objects.get_or_create(name="SmsWebhookCaller")
        webhook_group.user_set.add(webhooker)

        manager = User.objects.create_user(
            "manager", "paul2@carroll.com", "paulpassword"
        )
        manager_group, _ = Group.objects.get_or_create(name="SmsManager")
        manager_group.user_set.add(manager)

        User.objects.create_user("hacker", "hacked@carroll.com", "paulpassword")

        Question.objects.get_or_create(text="Why?")
        SmsUser.objects.get_or_create(
            phone_number="+13033033003", logged_in_user=webhooker
        )

    def test_bad_auth(self):
        user = User.objects.get(username="hacker")
        self.client.force_authenticate(user=user)
        response = self.client.get("/sms/users/", {})
        assert response.status_code == 403
        response = self.client.get("/sms/user/", {})
        assert response.status_code == 403
        response = self.client.post("/sms/data_point/", {})
        assert response.status_code == 403
        response = self.client.get("/sms/webhook/", {})
        assert response.status_code == 403

    def test_sms_webhook_group(self):
        user = User.objects.get(username="manager")
        self.client.force_authenticate(user=user)
        response = self.client.get("/sms/webhook/", {})
        assert response.status_code == 403

    def test_sms_manager_group(self):
        user = User.objects.get(username="webhooker")
        self.client.force_authenticate(user=user)
        response = self.client.get("/sms/data_point/", {})
        assert response.status_code == 403
        response = self.client.get("/sms/users/", {})
        assert response.status_code == 403
        response = self.client.get("/sms/user/", {})
        assert response.status_code == 403

    def test_get_users(self):
        user = User.objects.get(username="manager")
        self.client.force_authenticate(user=user)

        response = self.client.get("/sms/users/", {})
        assert response.status_code == 200
        assert "users" in response.data
        assert len(response.data["users"]) == 1

    def test_put_user(self):
        user = User.objects.get(username="manager")
        self.client.force_authenticate(user=user)

        question = Question.objects.get(text="Why?")
        sms_user = SmsUser.objects.get(phone_number="+13033033003")

        send_message_at_time_str = datetime.now(tz=timezone.utc).isoformat()

        response = self.client.put(
            "/sms/user/",
            {
                "id": sms_user.id,
                "phone_number": str(sms_user.phone_number),
                "questions": [question.to_dict_for_api()],
                "send_message_at_time": send_message_at_time_str,
            },
            format="json",
        )
        assert response.status_code == 200
        assert "user" in response.data
        assert response.data["user"]["send_message_at_time"] == send_message_at_time_str

    def test_create_data_point(self):
        user = User.objects.get(username="manager")
        self.client.force_authenticate(user=user)

        question = Question.objects.get(text="Why?")
        sms_user = SmsUser.objects.get(phone_number="+13033033003")

        response = self.client.post(
            "/sms/data_point/",
            {"question_id": question.id, "user_id": sms_user.id},
            format="json",
        )
        assert response.status_code == 201
        assert "data_point" in response.data

    def test_create_data_point_with_prayer_snippet(self):
        user = User.objects.get(username="manager")
        self.client.force_authenticate(user=user)

        # Create a new question with a callback.
        question = Question.objects.create(
            text="This creates prayer snippets.",
            callback="create_gratitude_prayer_snippet",
        )
        sms_user = SmsUser.objects.get(phone_number="+13033033003")

        response = self.client.post(
            "/sms/data_point/",
            {"question_id": question.id, "user_id": sms_user.id},
            format="json",
        )
        assert response.status_code == 201

        # No text means no prayer snippet.
        assert PrayerSnippet.objects.count() == 0

        # Try text and a score.
        snippet_text = "This is a prayer snippet."
        response = self.client.post(
            "/sms/data_point/",
            {
                "question_id": question.id,
                "user_id": sms_user.id,
                "text": snippet_text,
                "score": 3,
            },
            format="json",
        )
        assert response.status_code == 201
        assert "data_point" in response.data
        data_point_id = response.data["data_point"]["id"]
        snippet = PrayerSnippet.objects.get(sms_data_point_id=data_point_id)
        assert snippet_text == snippet.text
        assert snippet.type == "GRATITUDE"

    def test_webhook(self):
        user = User.objects.get(username="webhooker")
        self.client.force_authenticate(user=user)
        # No phone number provided.
        response = self.client.post("/sms/webhook/", {})
        assert response.status_code == 400

        # Garbage phone number provided.
        response = self.client.post(
            "/sms/webhook/", {"From": "+19999999999", "Body": "3"}
        )
        assert response.status_code == 400

        # Good phone number, but there isn't a DataPoint yet in the backend.
        response = self.client.post(
            "/sms/webhook/", {"From": "+13033033003", "Body": "3"}
        )
        assert response.status_code == 400

        question = Question.objects.get(text="Why?")
        sms_user = SmsUser.objects.get(phone_number="+13033033003")

        # Create a DataPoint that is too old.
        data_point, _ = DataPoint.objects.get_or_create(
            user=sms_user, question=question
        )
        data_point.created_at = datetime.now() - timedelta(minutes=30)
        data_point.save()
        response = self.client.post(
            "/sms/webhook/", {"From": "+13033033003", "Body": "3"}
        )
        assert response.status_code == 204

        # OK, now it's not too old, but it's already been populated.
        data_point.created_at = datetime.now()
        data_point.score = 3
        data_point.save()
        response = self.client.post(
            "/sms/webhook/", {"From": "+13033033003", "Body": "3"}
        )
        assert response.status_code == 204
        data_point.score = None
        data_point.save()

        # Let's create several DataPoints and make sure that we return the most recent one.
        DataPoint.objects.create(user=sms_user, question=question)
        DataPoint.objects.create(user=sms_user, question=question)
        most_recent_datapoint = DataPoint.objects.create(
            user=sms_user, question=question
        )

        # Now let's pass in some messages that can't be parsed.
        response = self.client.post(
            "/sms/webhook/", {"From": "+13033033003", "Body": ""}
        )
        assert response.status_code == 204
        response = self.client.post(
            "/sms/webhook/", {"From": "+13033033003", "Body": "eggplant"}
        )
        assert response.status_code == 204
        response = self.client.post(
            "/sms/webhook/", {"From": "+13033033003", "Body": "100"}
        )
        assert response.status_code == 204
        response = self.client.post(
            "/sms/webhook/", {"From": "+13033033003", "Body": "-1"}
        )
        assert response.status_code == 204

        # Finally we post a good message!
        response = self.client.post(
            "/sms/webhook/", {"From": "+13033033003", "Body": "3 testnote"}
        )
        assert response.status_code == 200
        # Reload from DB.
        most_recent_datapoint = DataPoint.objects.get(id=most_recent_datapoint.id)
        assert most_recent_datapoint.score == 3
        assert most_recent_datapoint.text == "testnote"


def to_local_time(time_str, timezone="America/Los_Angeles"):
    local_time = pytz.timezone(timezone)
    if time_str is None:
        localized_time = None
    else:
        localized_time = local_time.localize(datetime.strptime(time_str, "%Y-%m-%d"))
    return localized_time


class SmsHomeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create_user("paul", "paul@carroll.com", "paulpassword")

        cls.user2 = User.objects.create_user(
            "grace", "grace@boorstein.com", "gracepassword"
        )
        cls.sms_user_1 = SmsUser.objects.create(
            phone_number="+13033033003", logged_in_user=cls.user1
        )
        cls.sms_user_2 = SmsUser.objects.create(
            phone_number="+13033033023", logged_in_user=cls.user2
        )
        cls.question_1 = Question.objects.create(text="Why?")
        cls.question_2 = Question.objects.create(text="Why not?")

        cls.data_point_1_1 = DataPoint.objects.create(
            question=cls.question_1, user=cls.sms_user_1, score=1
        )
        cls.start_date_str_1_1 = "2020-10-10"
        cls.data_point_1_1.created_at = to_local_time(cls.start_date_str_1_1)
        cls.data_point_1_1.save()

        cls.data_point_1_2 = DataPoint.objects.create(
            question=cls.question_1, user=cls.sms_user_1, score=2
        )
        cls.start_date_str_1_2 = "2020-10-11"
        cls.data_point_1_2.created_at = to_local_time(cls.start_date_str_1_2)
        cls.data_point_1_2.save()

    def test_fetch_all_data_points(self):
        c = Client()
        c.force_login(self.user1)
        response = c.get("/sms/home/data_points/", {"question_id": self.question_1.id})
        self.assertEqual(response.status_code, 200)
        data_points = response.json()["data_points"]
        self.assertEqual(len(data_points), 2)

    def test_fetch_with_start_date(self):
        c = Client()
        c.force_login(self.user1)
        response = c.get(
            "/sms/home/data_points/",
            {"question_id": self.question_1.id, "start_date": "2020-10-11"},
        )
        self.assertEqual(response.status_code, 200)
        data_points = response.json()["data_points"]
        self.assertEqual(len(data_points), 1)

    def test_fetch_with_end_date(self):
        c = Client()
        c.force_login(self.user1)
        response = c.get(
            "/sms/home/data_points/",
            {"question_id": self.question_1.id, "end_date": "2020-10-11"},
        )
        self.assertEqual(response.status_code, 200)
        data_points = response.json()["data_points"]
        self.assertEqual(len(data_points), 1)

    def test_wrong_question(self):
        c = Client()
        c.force_login(self.user1)
        response = c.get("/sms/home/data_points/", {"question_id": self.question_2.id})
        self.assertEqual(response.status_code, 200)
        data_points = response.json()["data_points"]
        self.assertEqual(len(data_points), 0)

    def test_wrong_user(self):
        c = Client()
        c.force_login(self.user2)
        response = c.get("/sms/home/data_points/", {"question_id": self.question_1.id})
        self.assertEqual(response.status_code, 200)
        data_points = response.json()["data_points"]
        self.assertEqual(len(data_points), 0)

    def test_no_parse_date(self):
        c = Client()
        c.force_login(self.user1)
        response = c.get(
            "/sms/home/data_points/",
            {"question_id": self.question_1.id, "end_date": "2020-10-??11"},
        )
        self.assertEqual(response.status_code, 400)

    def test_no_logged_in(self):
        c = Client()
        response = c.get(
            "/sms/home/data_points/",
            {"question_id": self.question_1.id, "end_date": "2020-10-??11"},
        )
        self.assertEqual(response.status_code, 302)
