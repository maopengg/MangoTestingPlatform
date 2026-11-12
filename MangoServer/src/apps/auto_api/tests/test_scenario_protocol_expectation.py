from types import SimpleNamespace
from unittest import TestCase

from rest_framework import serializers

from src.apps.auto_api.exceptions import AutoApiError
from src.apps.auto_api.schemas.case_schema import (
    merge_scenario_protocol_config,
    unpack_scenario_body_config,
)
from src.apps.auto_api.services.api_case.parameter_validation import ApiCaseParameterValidationService
from src.apps.auto_api.services.execution.cases.test_case import TestCase as ApiCaseRunner


class ScenarioProtocolExpectationTest(TestCase):
    def test_posterior_json_extract_uses_key_value_contract(self):
        result = ApiCaseParameterValidationService.validate_extract(
            [{'key': 'attribute_id', 'value': '$.data.attributeId'}],
            '响应JSON提取',
        )

        self.assertEqual(result, [{
            'key': 'attribute_id',
            'value': '$.data.attributeId',
            'datasource_alias': None,
        }])

    def test_posterior_json_extract_rejects_json_path_as_expected_business_error(self):
        with self.assertRaises(AutoApiError) as context:
            ApiCaseParameterValidationService.validate_extract(
                [{'key': 'attribute_id', 'json_path': '$.data.attributeId'}],
                '响应JSON提取',
            )

        self.assertIn('响应JSON提取第1项格式错误', context.exception.msg)
        self.assertIn('不支持字段 json_path', context.exception.msg)

    def test_expectation_is_preserved_but_not_sent_as_request_body(self):
        stored = merge_scenario_protocol_config(
            {'source_type': 'value', 'body': {'name': 'demo'}},
            protocol_expectation={'mode': 'codes', 'status_codes': [422, '400', 422]},
        )
        request_body, _, _ = unpack_scenario_body_config('http', stored)

        self.assertEqual(stored['protocol_expectation']['status_codes'], [400, 422])
        self.assertNotIn('protocol_expectation', request_body)
        self.assertEqual(request_body['body']['name'], 'demo')

    def test_invalid_expected_http_status_is_rejected(self):
        with self.assertRaises(serializers.ValidationError):
            merge_scenario_protocol_config(
                {},
                protocol_expectation={'mode': 'codes', 'status_codes': [700]},
            )

    def test_legacy_jsonpath_assertion_can_identify_negative_status(self):
        parameter = SimpleNamespace(
            body_config=None,
            ass_general=None,
            ass_json_all=None,
            ass_text_all=None,
            ass_jsonpath=[{
                'actual': '$.code',
                'expect': '422',
                'method': 'p_is_equal_to',
            }],
            ass_schema=None,
        )
        response = SimpleNamespace(code=422)

        expected_codes, accept_any = ApiCaseRunner.resolve_protocol_expectation(parameter, response)

        self.assertEqual(expected_codes, [])
        self.assertTrue(accept_any)

    def test_legacy_business_error_assertion_preserves_common_negative_http_status(self):
        parameter = SimpleNamespace(
            body_config=None,
            ass_general=None,
            ass_json_all=None,
            ass_text_all=None,
            ass_jsonpath=[{
                'actual': '$.code',
                'expect': '400001007',
                'method': 'p_is_equal_to',
            }],
            ass_schema=None,
        )

        expected_codes, _ = ApiCaseRunner.resolve_protocol_expectation(
            parameter,
            SimpleNamespace(code=400),
        )

        self.assertEqual(expected_codes, [])

    def test_explicit_success_mode_keeps_public_http_success_rule(self):
        parameter = SimpleNamespace(
            body_config={'protocol_expectation': {'mode': 'success', 'status_codes': []}},
            ass_general=None,
            ass_sql=None,
            ass_json_all=None,
            ass_text_all=None,
            ass_jsonpath=[{'actual': '$.code', 'expect': '403'}],
            ass_schema=None,
        )

        expected_codes, accept_any = ApiCaseRunner.resolve_protocol_expectation(
            parameter,
            SimpleNamespace(code=403),
        )

        self.assertEqual(expected_codes, [])
        self.assertFalse(accept_any)
