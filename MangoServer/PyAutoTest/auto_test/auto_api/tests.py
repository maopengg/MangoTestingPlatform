# Create your tests here.

from django.test import TestCase


# from PyAutoTest.auto_test.auto_api.views.api_info import ApiInfoViews


class MyTestCase(TestCase):

    def test_user_info(self):
        url = "/api/case/api/info/run"
        response = self.client.get(url)
