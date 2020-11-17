from django.contrib.auth.models import User, Group
from rest_framework import status
from rest_framework.test import APITestCase

from sms.models import DataPoint, Question
from sms.models import User as SmsUser


class AccountTests(APITestCase):
    def setUp(self):
        webhooker = User.objects.create_user('webhooker', 'paul@carroll.com', 'paulpassword')
        webhook_group, _ = Group.objects.get_or_create(name='SmsWebhookCaller')
        webhook_group.user_set.add(webhooker)

        manager = User.objects.create_user('manager', 'paul2@carroll.com', 'paulpassword')
        manager_group, _ = Group.objects.get_or_create(name='SmsManager')
        manager_group.user_set.add(manager)

        User.objects.create_user('hacker', 'hacked@carroll.com', 'paulpassword')

        Question.objects.get_or_create(text="Why?")
        SmsUser.objects.get_or_create(phone_number="+13033033003")

    def test_bad_auth(self):
        user = User.objects.get(username='hacker')
        self.client.force_authenticate(user=user)
        response = self.client.get('/sms/users/', {})
        assert response.status_code == 403
        response = self.client.post('/sms/data_point/', {})
        assert response.status_code == 403
        response = self.client.get('/sms/webhook/', {})
        assert response.status_code == 403

    def test_sms_webhook_group(self):
        user = User.objects.get(username='manager')
        self.client.force_authenticate(user=user)
        response = self.client.get('/sms/webhook/', {})
        assert response.status_code == 403

    def test_sms_manager_group(self):
        user = User.objects.get(username='webhooker')
        self.client.force_authenticate(user=user)
        response = self.client.get('/sms/data_point/', {})
        assert response.status_code == 403
        response = self.client.get('/sms/users/', {})
        assert response.status_code == 403

    def test_get_users(self):
        user = User.objects.get(username='manager')
        self.client.force_authenticate(user=user)

        response = self.client.get('/sms/users/', {})
        assert response.status_code == 200
        assert "users" in response.data
        assert len(response.data["users"]) == 1

    def test_create_data_point(self):
        user = User.objects.get(username='manager')
        self.client.force_authenticate(user=user)

        question = Question.objects.get(text="Why?")
        sms_user = SmsUser.objects.get(phone_number="+13033033003")

        response = self.client.post('/sms/data_point/',
                                    {"question_id": question.id, "user_id": sms_user.id},
                                    format="json")
        assert response.status_code == 201
        assert "data_point" in response.data

    def test_webhook(self):
        user = User.objects.get(username='webhooker')
        self.client.force_authenticate(user=user)
        response = self.client.post('/sms/webhook/', {})
        assert response.status_code == 400
        # TODO: add many more tests!
