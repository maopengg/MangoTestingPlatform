from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from mangotools.data_processor import JsonTool, RegexTool
from mangotools.exceptions import MangoToolsError

from src.apps.auto_api.exceptions import AutoApiError
from src.apps.auto_api.api.serializers.api_case_detailed_parameter_mutation import ApiCaseDetailedParameterSerializers
from src.apps.auto_api.services.api_case.parameter_validation import ApiCaseParameterValidationService
from src.apps.auto_api.services.api_info.mutation import ApiInfoMutationService
from src.apps.auto_api.services.base.api_base_test_setup import APIBaseTestSetup
from src.apps.auto_api.services.base.case_parameter import CaseParameter
from src.common.decorators.error_response import error_response
from src.common.exceptions import CommonError
from src.common.responses.json_response import extract_jsonpath_value


class ExtractionErrorTests(SimpleTestCase):
    def setUp(self):
        environment_names = patch(
            'src.apps.system.services.system_config.SystemConfigService.get_environment_display_names',
            return_value={},
        )
        environment_names.start()
        self.addCleanup(environment_names.stop)

    def test_jsonpath_syntax_has_operation_and_cache_key(self):
        with self.assertRaises(CommonError) as raised:
            extract_jsonpath_value({}, '$.data[', operation='响应JSON提取', cache_key='saved_id')
        self.assertIn('响应JSON提取', raised.exception.msg)
        self.assertIn('saved_id', raised.exception.msg)
        self.assertIn('方括号不完整', raised.exception.msg)
        self.assertNotIn('未匹配到数据', raised.exception.msg)

    def test_valid_jsonpath_miss_is_not_syntax_error(self):
        with self.assertRaises(CommonError) as raised:
            extract_jsonpath_value({'code': 200}, '$.data', operation='响应JSON提取')
        self.assertIn('字段不存在', raised.exception.msg)
        self.assertNotIn('表达式或参数无效', raised.exception.msg)

    def test_jsonpath_source_type_is_its_own_error(self):
        with self.assertRaises(CommonError) as raised:
            extract_jsonpath_value('not-json-object', '$', operation='响应JSON提取')
        self.assertEqual(raised.exception.code, 1066)

    def test_runtime_regex_error_has_item_key_and_chinese_reason(self):
        setup = APIBaseTestSetup.__new__(APIBaseTestSetup)
        setup.test_data = SimpleNamespace(replace=lambda value: value)
        with self.assertRaises(AutoApiError) as raised:
            setup.api_info_posterior_json_re([{'key': 'saved_id', 'value': '(abc'}],
                                            SimpleNamespace(text='abc'))
        for expected in ('第1项', 'saved_id', '圆括号'):
            self.assertIn(expected, raised.exception.msg)

    def test_runtime_regex_assertion_error_is_a_business_error(self):
        with self.assertRaises(AutoApiError) as raised:
            CaseParameter._CaseParameter__extract_regex_assertion_value('abc', '[abc', 2)
        self.assertIn('第2项', raised.exception.msg)
        self.assertIn('方括号', raised.exception.msg)

    def test_cache_and_assertion_use_the_same_extracted_value(self):
        for text, expression, expected in (('a=1,b=2', r'a=(\d+),b=(\d+)', ['1', '2']),
                                           ('b', '(a)?b', None), ('', '^$', '')):
            with self.subTest(expression=expression):
                values = {}
                setup = APIBaseTestSetup.__new__(APIBaseTestSetup)
                setup.test_data = SimpleNamespace(replace=lambda value: value, set_cache=values.__setitem__)
                setup.api_info_posterior_json_re([{'key': 'result', 'value': expression}],
                                                SimpleNamespace(text=text))
                actual, _ = CaseParameter._CaseParameter__extract_regex_assertion_value(text, expression, 1)
                self.assertEqual(values['result'], expected)
                self.assertEqual(actual, expected)

    def test_save_rejects_invalid_extraction_configuration(self):
        for label, expression, expected in (('响应JSON提取', '$.data[', '方括号'),
                                             ('响应文本提取', '(abc', '圆括号')):
            with self.subTest(label=label), self.assertRaises(AutoApiError) as raised:
                ApiCaseParameterValidationService.validate_extract([{'key': 'result', 'value': expression}], label)
            self.assertIn('第1项', raised.exception.msg)
            self.assertIn(expected, raised.exception.msg)

    def test_save_rejects_invalid_assertion_expression(self):
        for kind, expression in (('regex', '['), ('jsonpath', '$.')):
            with self.subTest(kind=kind), self.assertRaises(AutoApiError):
                ApiCaseParameterValidationService.validate_jsonpath([
                    {'assertion_type': kind, 'actual': expression, 'method': 'p_is_none'},
                ])

    def test_dynamic_expression_is_validated_after_resolution(self):
        for label in ('响应JSON提取', '响应文本提取'):
            result = ApiCaseParameterValidationService.validate_extract(
                [{'key': 'result', 'value': '${{expression}}'}], label,
            )
            self.assertEqual(result[0]['value'], '${{expression}}')
        with self.assertRaises(MangoToolsError):
            RegexTool.compile('[')

    def test_api_info_save_validates_both_field_names(self):
        for field in ('posterior_json_path', 'posterior_response'):
            with self.subTest(field=field), self.assertRaises(AutoApiError):
                ApiInfoMutationService.split_payload({field: [{'key': 'result', 'value': '$.'}]})
        for field in ('posterior_re', 'posterior_response_text'):
            with self.subTest(field=field), self.assertRaises(AutoApiError):
                ApiInfoMutationService.split_payload({field: [{'key': 'result', 'value': '['}]})

    def test_http_serializer_uses_shared_expression_validation(self):
        serializer = ApiCaseDetailedParameterSerializers()
        for validator, expression in ((serializer.validate_posterior_response, '$.'),
                                      (serializer.validate_posterior_response_text, '[')):
            with self.subTest(expression=expression), self.assertRaises(AutoApiError):
                validator([{'key': 'result', 'value': expression}])
        with self.assertRaises(AutoApiError):
            serializer.validate_ass_jsonpath([
                {'assertion_type': 'jsonpath', 'actual': '$.', 'method': 'p_is_none'},
            ])

    def test_http_response_contains_our_message_not_internal_error(self):
        for operation, expected in ((lambda: JsonTool.get_json_path_value({}, '$.'), '点号'),
                                      (lambda: RegexTool.compile('[abc'), '方括号'),
                                      (lambda: extract_jsonpath_value({}, '$.data', operation='响应JSON提取'), '不存在字段')):
            @error_response('api')
            def endpoint(self, request):
                operation()

            with patch('src.common.decorators.error_response.report_system_error') as report:
                response = endpoint(None, SimpleNamespace(user={}))
            self.assertIn(expected, response.data['msg'])
            self.assertNotEqual(response.data['code'], 1000)
            self.assertNotIn('Traceback', response.data['msg'])
            report.assert_not_called()
