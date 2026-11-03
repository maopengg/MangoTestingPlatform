from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from mangotools.enums import StatusEnum

from src.apps.auto_api.enums.assertion import ApiDefaultAssertionCheck as Check
from src.apps.auto_api.schemas.execution import ApiExecutionResponse
from src.apps.auto_api.services.base.case_parameter import CaseParameter
from src.apps.auto_api.services.protocols.outcome import ProtocolCallOutcomeService as Outcome
from src.apps.auto_api.services.test_case.test_case_parts.protocol import ApiTestCaseProtocolMixin
from src.apps.system.services.enum_catalog import EnumCatalogService
from src.apps.system.services.system_config import (
    API_DEFAULT_ASSERTION_ENABLED_KEY, API_DEFAULT_ASSERTION_CHECKS_KEY,
    SystemConfigService, get_config_definition_map,
)


def response(protocol='http', **values):
    return ApiExecutionResponse(**{
        'code': 200 if protocol == 'http' else None, 'headers': {}, 'time': 0,
        'request_protocol_type': protocol, 'response_mode': protocol, **values,
    })


class DefaultAssertionConfigTests(SimpleTestCase):
    def test_registered_defaults_are_off_and_checks_have_options(self):
        definitions = get_config_definition_map()
        self.assertFalse(definitions[API_DEFAULT_ASSERTION_ENABLED_KEY].default_value)
        self.assertEqual(definitions[API_DEFAULT_ASSERTION_CHECKS_KEY].default_value, Check.defaults())
        with patch.object(SystemConfigService, 'get_environment_display_names', return_value={}):
            self.assertEqual(EnumCatalogService.catalog()['api_default_assertion_check'], Check.get_option())

    def test_checks_validate_list_and_reject_unknown_values(self):
        for value in ([], ['http_status'], '["mcp_result","grpc_status"]'):
            self.assertIsNone(SystemConfigService.validate_editable_config(API_DEFAULT_ASSERTION_CHECKS_KEY, value))
        for value in ({}, [True], ['anything'], 'http_status'):
            self.assertIsNotNone(SystemConfigService.validate_editable_config(API_DEFAULT_ASSERTION_CHECKS_KEY, value))

    def test_runtime_switch_and_empty_selection(self):
        with patch.object(SystemConfigService, 'get', return_value=False) as get:
            self.assertEqual(Outcome.default_checks(), frozenset())
            get.assert_called_once_with(API_DEFAULT_ASSERTION_ENABLED_KEY, default=False)
            self.assertTrue(Outcome.evaluate(response(code=500)).success)
        with patch.object(SystemConfigService, 'get', side_effect=[True, []]):
            self.assertEqual(Outcome.default_checks(), frozenset())
        with patch.object(SystemConfigService, 'get', side_effect=[True, ['mcp_result']]):
            self.assertEqual(Outcome.default_checks(), {Check.MCP_RESULT})

    def test_each_check_can_be_disabled_without_disabling_others(self):
        cases = [
            (Check.HTTP_STATUS, response(code=500)),
            (Check.GRAPHQL_ERRORS, response('graphql', code=200, json={'errors': ['invalid']})),
            (Check.JSON_RPC_ERROR, response('json_rpc', code=200, json={'error': {'code': -1}})),
            (Check.XML_FAULT, response('soap', code=200, text='<Envelope><Fault>invalid</Fault></Envelope>')),
            (Check.XML_FAULT, response('xml_rpc', code=200, text='<methodResponse><fault>invalid</fault></methodResponse>')),
            (Check.MCP_RESULT, response('mcp', mcp_is_error=True)),
            (Check.GRPC_STATUS, response('grpc', grpc_status_code='NOT_FOUND')),
            (Check.WEBSOCKET_CLOSE, response('websocket', code=101, ws_close_code=4001)),
            (Check.WEBSOCKET_HANDSHAKE, response('websocket', code=403)),
        ]
        for check, result in cases:
            with self.subTest(check=check, protocol=result.response_mode):
                self.assertFalse(Outcome.evaluate(result, default_checks=frozenset({check})).success)
                self.assertTrue(Outcome.evaluate(result, default_checks=frozenset()).success)

    def test_explicit_http_expectations_override_global_switch(self):
        self.assertFalse(Outcome.evaluate(response(code=400), require_http_success=True, default_checks=frozenset()).success)
        for checks in (frozenset(), frozenset(Check)):
            self.assertTrue(Outcome.evaluate(response(code=400), expected_http_status_codes=[400], default_checks=checks).success)
            self.assertFalse(Outcome.evaluate(response(code=200), expected_http_status_codes=[400], default_checks=checks).success)

    def test_http_auto_with_user_assertions_still_reaches_user_assertions(self):
        parameter = SimpleNamespace(body_config=None, ass_general=[{'method': 'equals'}])
        codes, any_status = ApiTestCaseProtocolMixin.resolve_protocol_expectation(parameter, response(code=400))
        self.assertTrue(Outcome.evaluate(response(code=400), expected_http_status_codes=codes,
                                        accept_any_http_status=any_status, default_checks=frozenset(Check)).success)

    def test_explicit_native_expectations_do_not_get_rejected_by_other_defaults(self):
        for checks in (frozenset(), frozenset(Check)):
            self.assertTrue(Outcome.evaluate(response('grpc', grpc_status_code='NOT_FOUND'),
                                            expected_grpc_status='NOT_FOUND', default_checks=checks).success)
            self.assertTrue(Outcome.evaluate(response('grpc', grpc_status_code='NOT_FOUND'),
                                            expected_grpc_status='ANY', default_checks=checks).success)
            self.assertFalse(Outcome.evaluate(response('grpc', grpc_status_code='OK'),
                                             expected_grpc_status='NOT_FOUND', default_checks=checks).success)
            self.assertTrue(Outcome.evaluate(response('mcp', mcp_is_error=True),
                                            expected_mcp_result='any', default_checks=checks).success)
            self.assertTrue(Outcome.evaluate(response('mcp', mcp_is_error=True),
                                            expected_mcp_result='error', default_checks=checks).success)
            self.assertFalse(Outcome.evaluate(response('mcp', mcp_is_error=False),
                                             expected_mcp_result='error', default_checks=checks).success)

    def test_no_response_and_real_failures_never_pass_with_defaults_off(self):
        for result in (
            response(code=None), response(code=0), response(error_msg='post processing failed'),
            response('mcp', mcp_protocol_error={'code': -32603}),
            response('websocket', ws_close_code=1006),
            *(response('grpc', grpc_status_code=status) for status in ('UNAVAILABLE', 'DEADLINE_EXCEEDED', 'UNKNOWN')),
        ):
            with self.subTest(protocol=result.response_mode, status=result.grpc_status_code):
                self.assertFalse(Outcome.evaluate(result, default_checks=frozenset()).success)

    def test_public_posterior_does_not_extract_from_negative_response(self):
        with patch.object(SystemConfigService, 'get', return_value=False):
            self.assertFalse(Outcome.should_run_api_info_posterior(response(code=400)))
            self.assertFalse(Outcome.should_run_api_info_posterior(response('mcp', mcp_is_error=True)))
            self.assertFalse(Outcome.should_run_api_info_posterior(response('grpc', grpc_status_code='NOT_FOUND')))

    def test_removed_duplicate_tasks_do_not_override_disabled_defaults(self):
        parameter = CaseParameter.__new__(CaseParameter)
        parameter.parameter = SimpleNamespace(ass_jsonpath=None, ass_sql=None, ass_general=None,
                                              ass_json_all=None, ass_text_all=None, ass_schema=None)
        for result in (response('mcp', mcp_is_error=True), response('grpc', grpc_status_code='NOT_FOUND')):
            _, status, error = parameter.verify_all_assertions(result)
            self.assertEqual(status, StatusEnum.SUCCESS.value)
            self.assertIsNone(error)
