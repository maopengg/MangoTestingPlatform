# Create your tests here.

from types import SimpleNamespace

from django.test import SimpleTestCase, TestCase

from src.apps.auto_api.schemas.case_schema import ApiParametrizeSuite
from src.apps.auto_api.service.base.case_base import CaseBase
from src.apps.auto_api.service.base.case_parameter import CaseParameter
from src.common.exceptions import ApiError
from src.common.models.api_model import RequestModel, ResponseModel


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


class ApiResponseJsonScalarTests(SimpleTestCase):

    class FakeTestData:

        def replace(self, value):
            return value

        def get_json_path_value(self, response, expression):
            return response[expression]

    def make_case_parameter(self):
        test_setup = SimpleNamespace(test_data=self.FakeTestData(), test_object=None)
        parameter = SimpleNamespace()
        api_info = SimpleNamespace(is_schema=0, ass_schema=None)
        return CaseParameter(test_setup, parameter, api_info)

    def test_response_model_accepts_json_scalar_values(self):
        for value in [True, False, 'ok', 1, 1.5, None, {'ok': True}, [1]]:
            response = ResponseModel(
                code=200,
                time=0.1,
                headers={},
                json=value,
                text='true' if value is True else str(value),
            )

            self.assertEqual(response.json, value)

    def test_request_model_allows_json_scalar_body(self):
        request = RequestModel(method='POST', url='https://example.test', json='true')

        request.serialize()

        self.assertIs(request.json, True)

    def test_jsonpath_assertion_rejects_scalar_response_with_business_error(self):
        case_parameter = self.make_case_parameter()

        with self.assertRaises(ApiError) as context:
            case_parameter._CaseParameter__ass_jsonpath(True, [
                {'actual': '$.success', 'method': 'p_is_true', 'expect': None}
            ])

        self.assertIn('不支持JSONPath处理', context.exception.msg)

    def test_text_assertion_supports_boolean_response_text(self):
        case_parameter = self.make_case_parameter()

        case_parameter._CaseParameter__ass_test_all('true', 'true')

        self.assertEqual(case_parameter.ass_result[0].status, 1)
