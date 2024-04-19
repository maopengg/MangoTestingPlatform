# Create your tests here.

from django.test import TestCase


class MyTestCase(TestCase):

    def test_user_info(self):
        url = "/api/case/api/info/run"
        response = self.client.get(url)
        print(response.json())
