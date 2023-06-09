# Create your tests here.
from django.test import TestCase

from PyAutoTest.auto_test.auto_api.case_data_processing.run_api_send import RunApiSend


def add(a, b):
    return a + b


class AddTestCase(TestCase):
    def test_add(self):
        RunApiSend.get_api_case_data(1)
