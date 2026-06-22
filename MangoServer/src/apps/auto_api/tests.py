# Create your tests here.

from types import SimpleNamespace

from django.test import SimpleTestCase, TestCase

from src.apps.auto_api.schemas.case_schema import ApiParametrizeSuite
from src.apps.auto_api.models import ApiInfo
from src.apps.auto_api.service.base.api_base_test_setup.base_request import BaseRequest
from src.apps.auto_api.service.base.api_base_test_setup import APIBaseTestSetup
from src.apps.auto_api.service.base.api_base_test_setup.request_body import prepare_request_body
from src.apps.auto_api.service.base.case_base import CaseBase
from src.apps.auto_api.service.base.case_parameter import CaseParameter
from src.apps.auto_api.views.api_case_detailed_parameter import ApiCaseDetailedParameterSerializers
from src.apps.auto_api.views.api_info import ApiInfoSerializers
from src.apps.system.models import ProductModule, Project, ProjectProduct
from src.common.exceptions import ApiError
from src.common.models.api_model import RequestModel, ResponseModel


class MyTestCase(TestCase):

    def test_user_info(self):
        url = "/api/case/api/info/run"
        response = self.client.get(url)
        print(response.json())


class ApiInfoDuplicateValidationTests(TestCase):

    def setUp(self):
        project = Project.objects.create(name='重复校验项目')
        self.product = ProjectProduct.objects.create(project=project, name='主服务')
        self.module = ProductModule.objects.create(project_product=self.product, name='模块A')

    def make_payload(self, name='接口A'):
        return {
            'project_product': self.product.id,
            'module': self.module.id,
            'type': 1,
            'name': name,
            'url': '/ai/unbox-chat/message',
            'method': 1,
            'headers': None,
            'params': None,
            'protocol_type': 'http',
            'body_type': 'none',
            'body_config': None,
            'sse_config': None,
        }

    def test_api_info_rejects_duplicate_route_identity(self):
        ApiInfo.objects.create(
            project_product=self.product,
            module=self.module,
            type=1,
            name='已有接口',
            url='/ai/unbox-chat/message',
            method=1,
            headers=None,
            protocol_type='http',
            body_type='none',
        )

        serializer = ApiInfoSerializers(data=self.make_payload('重复接口'))

        self.assertFalse(serializer.is_valid())
        self.assertIn('url', serializer.errors)

    def test_api_info_allows_updating_self(self):
        api_info = ApiInfo.objects.create(
            project_product=self.product,
            module=self.module,
            type=1,
            name='已有接口',
            url='/ai/unbox-chat/message',
            method=1,
            headers=None,
            protocol_type='http',
            body_type='none',
        )

        serializer = ApiInfoSerializers(instance=api_info, data={'name': '改名'}, partial=True)

        self.assertTrue(serializer.is_valid(), serializer.errors)


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
        request = RequestModel(
            method='POST',
            url='https://example.test',
            body_type='json',
            body_config={'source_type': 'template', 'body_text': 'true'},
        )

        request.serialize()

        self.assertEqual(request.body_type, 'json')
        self.assertEqual(request.body_config['body_text'], 'true')

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

    def test_jsonpath_assertion_or_group_passes_when_any_item_passes(self):
        case_parameter = self.make_case_parameter()

        case_parameter._CaseParameter__ass_jsonpath({'$.code': 201}, [
            {
                'group_name': '状态码兼容',
                'group_logic': 'OR',
                'actual': '$.code',
                'method': 'p_is_equal_to',
                'expect': 200,
            },
            {
                'group_name': '状态码兼容',
                'group_logic': 'OR',
                'actual': '$.code',
                'method': 'p_is_equal_to',
                'expect': 201,
            },
        ])

        self.assertEqual(case_parameter.ass_result[-1].status, 1)
        self.assertEqual(case_parameter.ass_result[-1].group_logic, 'OR')

    def test_jsonpath_assertion_without_group_logic_keeps_and_behavior(self):
        case_parameter = self.make_case_parameter()

        with self.assertRaises(ApiError):
            case_parameter._CaseParameter__ass_jsonpath({'$.code': 201}, [
                {'actual': '$.code', 'method': 'p_is_equal_to', 'expect': 200},
                {'actual': '$.code', 'method': 'p_is_equal_to', 'expect': 201},
            ])


class RequestModelParamsTests(SimpleTestCase):

    def test_params_allows_query_string(self):
        request = RequestModel(method='GET', url='https://example.test', params='case_id=21')

        request.serialize()

        self.assertEqual(request.params, 'case_id=21')

    def test_params_keeps_json_scalar_as_query_string(self):
        request = RequestModel(method='GET', url='https://example.test', params='21')

        request.serialize()

        self.assertEqual(request.params, '21')

    def test_params_still_parses_json_object_and_array(self):
        request = RequestModel(method='GET', url='https://example.test', params='{"case_id": 21}')
        request.serialize()
        self.assertEqual(request.params, {'case_id': 21})

        request = RequestModel(method='GET', url='https://example.test', params='[["case_id", 21]]')
        request.serialize()
        self.assertEqual(request.params, [['case_id', 21]])

    def test_params_rejects_malformed_json_object(self):
        request = RequestModel(method='GET', url='https://example.test', params='{"case_id":')

        with self.assertRaises(ApiError):
            request.serialize()


class RequestBodyRawTests(SimpleTestCase):

    def test_raw_body_defaults_to_application_json(self):
        request = RequestModel(
            method='POST',
            url='https://example.test',
            body_type='raw',
            body_config={'body_text': '{"ok": true}'},
        )

        prepared_body = prepare_request_body(request, None)

        self.assertEqual(prepared_body.content_type, 'application/json')
        self.assertEqual(prepared_body.kwargs, {'content': '{"ok": true}'})

    def test_content_type_header_is_added_when_missing(self):
        headers = BaseRequest._headers_with_content_type({'Accept': 'application/json'}, 'application/json')

        self.assertEqual(headers, {'Accept': 'application/json', 'Content-Type': 'application/json'})

    def test_content_type_header_keeps_user_value(self):
        headers = BaseRequest._headers_with_content_type({'content-type': 'application/xml'}, 'application/json')

        self.assertEqual(headers, {'content-type': 'application/xml'})

    def test_multipart_content_type_header_is_removed(self):
        headers = BaseRequest._headers_with_content_type(
            {'Accept': 'application/json', 'Content-Type': 'multipart/form-data'},
            'multipart/form-data',
        )

        self.assertEqual(headers, {'Accept': 'application/json'})

    def test_api_info_serializer_defaults_raw_content_type(self):
        serializer = ApiInfoSerializers()

        attrs = serializer.validate({'body_type': 'raw', 'body_config': {'body_text': 'hello'}})

        self.assertEqual(attrs['body_config']['content_type'], 'application/json')

    def test_api_info_serializer_drops_legacy_body_fields(self):
        serializer = ApiInfoSerializers()

        attrs = serializer.validate({'data': '{"a": 1}', 'json': '{"b": 2}', 'file': [], 'is_text_data': 1})

        self.assertNotIn('data', attrs)
        self.assertNotIn('json', attrs)
        self.assertNotIn('file', attrs)
        self.assertNotIn('is_text_data', attrs)


class ApiPosteriorRegexTests(SimpleTestCase):

    class FakeTestData:

        def replace(self, value):
            return value

    def test_invalid_regex_raises_business_error(self):
        test_setup = APIBaseTestSetup.__new__(APIBaseTestSetup)
        test_setup.test_data = self.FakeTestData()
        response = ResponseModel(code=200, time=0.1, headers={}, text='hello')

        with self.assertRaises(ApiError) as context:
            test_setup.api_info_posterior_json_re(
                [{'key': 'token', 'value': '(?<=a+)b'}],
                response,
            )

        self.assertIn('后置正则表达式错误', context.exception.msg)

    def test_api_case_parameter_serializer_defaults_raw_content_type(self):
        serializer = ApiCaseDetailedParameterSerializers()

        attrs = serializer.validate({'body_type': 'raw', 'body_config': {'body_text': 'hello'}})

        self.assertEqual(attrs['body_config']['content_type'], 'application/json')

    def test_api_case_parameter_serializer_drops_legacy_body_fields(self):
        serializer = ApiCaseDetailedParameterSerializers()

        attrs = serializer.validate({'data': '{"a": 1}', 'json': '{"b": 2}', 'file': []})

        self.assertNotIn('data', attrs)
        self.assertNotIn('json', attrs)
        self.assertNotIn('file', attrs)
