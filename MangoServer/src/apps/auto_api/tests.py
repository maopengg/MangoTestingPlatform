# Create your tests here.

from types import SimpleNamespace

from django.test import SimpleTestCase, TestCase

from src.apps.auto_api.schemas.case_schema import ApiParametrizeSuite
from src.apps.auto_api.service.base.case_base import CaseBase
from src.common.exceptions import ApiError


class MyTestCase(TestCase):

    def test_user_info(self):
        url = "/api/case/api/info/run"
        response = self.client.get(url)
        print(response.json())


class CaseBaseParametrizeTests(SimpleTestCase):

    class FakeTestData:

        def __init__(self):
            self.cache = {}

        def replace(self, value):
            return value

        def set_cache(self, key, value):
            self.cache[key] = value

    def make_case_base(self):
        test_data = self.FakeTestData()
        test_setup = SimpleNamespace(test_data=test_data)
        return CaseBase(test_setup, SimpleNamespace()), test_data

    def test_case_parametrize_allows_empty_values(self):
        case_base, test_data = self.make_case_base()

        case_base.case_parametrize({
            'parametrize': [
                {'key': 'empty_text', 'value': ''},
                {'key': 'null_value', 'value': None},
                {'key': 'missing_value'},
                {'key': 'zero_value', 'value': 0},
                {'key': 'false_value', 'value': False},
                {'key': 'empty_list', 'value': []},
            ]
        })

        self.assertEqual(test_data.cache, {
            'empty_text': '',
            'null_value': None,
            'missing_value': None,
            'zero_value': 0,
            'false_value': False,
            'empty_list': [],
        })

    def test_case_parametrize_still_rejects_empty_key(self):
        case_base, _ = self.make_case_base()

        with self.assertRaises(ApiError):
            case_base.case_parametrize({'parametrize': [{'key': '', 'value': 'ok'}]})

    def test_parametrize_schema_allows_null_and_missing_values(self):
        parametrize = ApiParametrizeSuite.model_validate({
            'name': '参数组1',
            'parametrize': [
                {'key': 'null_value', 'value': None},
                {'key': 'missing_value'},
            ]
        })

        self.assertEqual(parametrize.model_dump(), {
            'name': '参数组1',
            'parametrize': [
                {'key': 'null_value', 'value': None},
                {'key': 'missing_value', 'value': None},
            ],
        })
