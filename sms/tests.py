from datetime import datetime, timedelta, timezone

from django.contrib.auth.models import User, Group
from rest_framework import status
from rest_framework.test import APITestCase

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
        SmsUser.objects.get_or_create(phone_number="+13033033003")

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
