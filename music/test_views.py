from django.test import TransactionTestCase
from django.urls import reverse


class ViewsTestCase(TransactionTestCase):
    fixtures = ['db_contents_06032019.json']

    def test_views(self):
        response = self.client.get(reverse('music:music_detailed', args=[1]))
        assert response.status_code == 200
