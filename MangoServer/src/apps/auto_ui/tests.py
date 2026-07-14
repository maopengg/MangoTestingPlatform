# Create your tests here.
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from src.apps.auto_ui.service.test_case import test_case as ui_test_case_module
from src.apps.auto_ui.service.test_case.test_case import TestCase
from src.common.exceptions import UiError


class FakeQuerySet(list):

    def order_by(self, *args):
        return self


class UiTestCaseParametrizeTests(SimpleTestCase):


    def test_case_parametrize_allows_empty_values(self):
        case = self.make_case([
            {
                'name': '参数组1',
                'parametrize': [
                    {'key': 'empty_text', 'value': ''},
                    {'key': 'null_value', 'value': None},
                    {'key': 'missing_value'},
                    {'key': 'zero_value', 'value': 0},
                    {'key': 'false_value', 'value': False},
                    {'key': 'empty_list', 'value': []},
                ],
            }
        ])

        self.assertIsNotNone(self.run_case(case))

    def test_case_parametrize_still_rejects_empty_key(self):
        case = self.make_case([{'name': '参数组1', 'parametrize': [{'key': '', 'value': 'ok'}]}])

        with self.assertRaises(UiError):
            self.run_case(case)
