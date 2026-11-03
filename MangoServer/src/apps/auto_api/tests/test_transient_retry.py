from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from django.db import DatabaseError

from src.apps.auto_api.enums import ApiBodyTypeEnum, ApiProtocolTypeEnum, MethodEnum
from src.apps.auto_api.enums.retry import ApiTransientRetryCondition as Condition
from src.apps.auto_api.enums.assertion import ApiDefaultAssertionCheck
from src.apps.auto_api.exceptions import (
    API_REQUEST_TIMEOUT, API_TARGET_NO_RESPONSE, API_TLS_FAILED, AutoApiError, TestSuiteStopped,
)
from src.apps.auto_api.schemas.execution import ApiExecutionResponse
from src.apps.auto_api.services.test_case.transient_retry import ApiTransientRetryService as Retry
from src.apps.auto_api.services.test_case.test_case_parts.parameter import ApiTestCaseParameterMixin
from src.apps.system.services.system_config import (
    API_TRANSIENT_RETRY_ENABLED_KEY, API_TRANSIENT_RETRY_CONDITIONS_KEY,
    SystemConfigService, get_config_definition_map,
)


class TransientRetryTests(SimpleTestCase):
    def test_defaults_are_enabled_and_exclude_500_and_assertions(self):
        definitions = get_config_definition_map()
        self.assertTrue(definitions[API_TRANSIENT_RETRY_ENABLED_KEY].default_value)
        self.assertEqual(definitions[API_TRANSIENT_RETRY_CONDITIONS_KEY].default_value, Condition.defaults())
        self.assertNotIn(Condition.HTTP_500.value, Condition.defaults())
        self.assertNotIn(Condition.ASSERTION.value, Condition.defaults())

    def test_conditions_allow_empty_list_but_reject_arbitrary_values(self):
        for value in ([], ['http_500', 'assertion_failed'], '["timeout"]'):
            self.assertIsNone(SystemConfigService.validate_editable_config(API_TRANSIENT_RETRY_CONDITIONS_KEY, value))
        for value in ('timeout', {}, [500], ['business_code_110000']):
            self.assertIsNotNone(SystemConfigService.validate_editable_config(API_TRANSIENT_RETRY_CONDITIONS_KEY, value))

    def test_classification_uses_error_definitions_and_http_not_business_codes(self):
        self.assertEqual(Retry.error_condition(AutoApiError(API_REQUEST_TIMEOUT, value=('timeout',))), Condition.TIMEOUT)
        self.assertEqual(Retry.error_condition(AutoApiError(API_TARGET_NO_RESPONSE, value=('closed',))), Condition.CONNECTION)
        self.assertIsNone(Retry.error_condition(AutoApiError(API_TLS_FAILED, value=('certificate',))))
        self.assertIsNone(Retry.error_condition(RuntimeError('timeout')))
        response = ApiExecutionResponse(code=200, headers={}, time=0, json={'code': 503})
        self.assertIsNone(Retry.response_condition(response, call_success=False))
        self.assertEqual(Retry.response_condition(response, call_success=True), Condition.ASSERTION)

    def test_disable_and_empty_selection_really_disable_retry(self):
        with patch.object(SystemConfigService, 'get', side_effect=DatabaseError('unavailable')):
            self.assertFalse(Retry.selected(Condition.TIMEOUT))
        with patch.object(SystemConfigService, 'get', return_value=False):
            self.assertFalse(Retry.selected(Condition.TIMEOUT))
        with patch.object(SystemConfigService, 'get', side_effect=[True, []]):
            self.assertFalse(Retry.selected(Condition.TIMEOUT))
        with patch.object(SystemConfigService, 'get', side_effect=[True, ['assertion_failed']]):
            self.assertTrue(Retry.selected(Condition.ASSERTION))

    def test_unsafe_contexts_are_never_automatically_retried(self):
        request = SimpleNamespace(protocol_type='http', method='GET')
        parameter = SimpleNamespace()
        api = SimpleNamespace()
        self.assertTrue(Retry.safe(request, parameter, api))
        for key in ('recovery', 'callbacks', 'factory_ran', 'gray'):
            self.assertFalse(Retry.safe(request, parameter, api, **{key: True}))
        for field in ('front_sql', 'front_func', 'posterior_sql', 'posterior_func', 'posterior_file',
                      'posterior_response', 'posterior_response_text'):
            self.assertFalse(Retry.safe(request, SimpleNamespace(**{field: ['configured']}), api))
        self.assertFalse(Retry.safe(request, parameter, SimpleNamespace(posterior_func='custom')))
        for method in ('POST', 'PUT', 'DELETE', 'PATCH'):
            request.method = method
            self.assertFalse(Retry.safe(request, parameter, api))
        request.method = 'GET'
        request.protocol_type = 'sse'
        self.assertFalse(Retry.safe(request, parameter, api))


class TransientRetryExecutionTests(SimpleTestCase):
    def execute(self, responses, *, selected=None, assertions=None, retry=1, method=MethodEnum.GET.value,
                cleanup_error=None, stopped=False, default_checks=frozenset(ApiDefaultAssertionCheck)):
        path = 'src.apps.auto_api.services.test_case.test_case_parts.parameter'
        api = SimpleNamespace(id=7, project_product_id=9, name='查询', method=method,
                              protocol_type=ApiProtocolTypeEnum.HTTP.value, body_type=ApiBodyTypeEnum.NONE.value,
                              url='https://example.com/search', posterior_func=None)
        parameter = SimpleNamespace(id=2, name='查询场景', error_retry=retry, retry_interval=0,
                                    params=None, body_config=None, sse_config=None, allow_failure=False,
                                    front_sql=[], front_func=None, posterior_sql=[], posterior_func=None,
                                    posterior_file={}, posterior_response=[], posterior_response_text=[],
                                    ass_jsonpath=[], ass_general=[], ass_json_all={}, ass_text_all=None, ass_schema=None)
        step = SimpleNamespace(id=1, api_info_id=7, api_info=api, execution_config={})
        runtime = ApiTestCaseParameterMixin()
        self.runtime = runtime
        runtime.revision_aggregate = Mock()
        runtime.revision_aggregate.data_factory_configs_for.return_value = []
        runtime.is_step_debug = False
        runtime.current_step_execution_context = None
        runtime.test_env = 0
        runtime.user_id = 1
        runtime.case_id = 1
        runtime.test_suite = runtime.test_suite_details = None
        runtime.api_case = SimpleNamespace(callback_checks=[], front_public=[], front_auth_config=[])
        runtime.case_base = SimpleNamespace(case_headers=[])
        runtime.api_case_result = SimpleNamespace(steps=[], callback_results=[])
        runtime.test_setup = Mock()
        runtime.test_setup.test_data.get_all.return_value = {}
        runtime.test_setup.test_data.get_data_factory_all.return_value = {}
        runtime.test_setup.api_request.side_effect = responses
        runtime.get_parameters_for_step = Mock(return_value=[parameter])
        runtime.trace_recorder = Mock()
        runtime.trace_recorder.start_step.side_effect = lambda *args, **kwargs: SimpleNamespace(id=1, status=3)
        runtime.gray_trace_summary = Mock(return_value={})
        runtime.restore_gray_with_trace = Mock()
        runtime.resolve_protocol_expectation = Mock(return_value=([], False))
        runtime.has_user_configured_assertions = Mock(return_value=True)
        runtime.resolve_scenario_result_name = Mock(return_value='查询场景')
        runtime.raise_if_report_stopped = Mock(side_effect=TestSuiteStopped() if stopped else None)
        runtime.update_test_case_detailed_parameter = Mock()
        with patch(path + '.ParameterDataFactory') as factory, patch(path + '.CaseParameter') as scenario, \
                patch(path + '.GrayCaseExecutionRunner.apply_api_parameter', return_value=[]), \
                patch(path + '.GrayCaseExecutionRunner.api_case_snapshot', return_value={}), \
                patch.object(Retry, 'selected', side_effect=lambda c: c in (selected if selected is not None else Condition.defaults())), \
                patch(path + '.ProtocolCallOutcomeService.default_checks', return_value=default_checks), \
                patch(path + '.time.sleep') as sleep:
            factory.return_value.runner = SimpleNamespace(execution_ids=[])
            factory.return_value.cleanup.side_effect = cleanup_error
            scenario.return_value.headers.return_value = {}
            scenario.return_value.front_main.side_effect = lambda request: request
            scenario.return_value.posterior_main.side_effect = lambda response: response
            scenario.return_value.ass_main.side_effect = assertions or [([], 1, None)]
            result = runtime.detailed_parameter(step)
        return runtime, result, sleep

    def response(self, code):
        return ApiExecutionResponse(code=code, headers={}, time=0.1, json={})

    def test_http_transient_failure_retries_once_and_retains_both_results(self):
        runtime, result, sleep = self.execute([self.response(503), self.response(200)])
        self.assertIsNone(result)
        self.assertEqual([s.status for s in runtime.api_case_result.steps], [0, 1])
        self.assertEqual(runtime.api_case_result.steps[-1].automatic_retry_condition, 'http_503')
        self.assertEqual(runtime.test_setup.api_request.call_count, 2)
        sleep.assert_called_once_with(2)

    def test_disabled_defaults_allow_response_to_reach_posterior_and_assertions(self):
        runtime, result, sleep = self.execute([self.response(400)], default_checks=frozenset())
        self.assertIsNone(result)
        self.assertEqual(runtime.api_case_result.steps[0].status, 1)
        self.assertEqual(runtime.test_setup.api_request.call_count, 1)
        sleep.assert_not_called()

    def test_transport_failure_retries_but_never_more_than_once(self):
        error = AutoApiError(API_TARGET_NO_RESPONSE, value=('closed',))
        runtime, result, _ = self.execute([error, error])
        self.assertEqual(runtime.test_setup.api_request.call_count, 2)
        self.assertEqual(len(runtime.api_case_result.steps), 2)
        self.assertEqual(result[0], 0)

    def test_business_assertions_require_explicit_selection(self):
        runtime, _, _ = self.execute([self.response(200)], assertions=[([], 0, '不匹配')])
        self.assertEqual(runtime.test_setup.api_request.call_count, 1)
        runtime, result, _ = self.execute([self.response(200), self.response(200)],
                                         selected=['assertion_failed'], assertions=[([], 0, '不匹配'), ([], 1, None)])
        self.assertIsNone(result)
        self.assertEqual(runtime.api_case_result.steps[-1].automatic_retry_condition, 'assertion_failed')

    def test_manual_retries_are_not_multiplied_and_write_requests_do_not_retry(self):
        runtime, _, _ = self.execute([self.response(503), self.response(503)], retry=2)
        self.assertEqual(runtime.test_setup.api_request.call_count, 2)
        self.assertTrue(all(s.automatic_retry_condition is None for s in runtime.api_case_result.steps))
        runtime, _, _ = self.execute([self.response(503)], method=MethodEnum.POST.value)
        self.assertEqual(runtime.test_setup.api_request.call_count, 1)

    def test_http_500_requires_opt_in(self):
        runtime, _, _ = self.execute([self.response(500)])
        self.assertEqual(runtime.test_setup.api_request.call_count, 1)
        runtime, _, _ = self.execute([self.response(500), self.response(200)], selected=['http_500'])
        self.assertEqual(runtime.test_setup.api_request.call_count, 2)

    def test_cleanup_failure_or_stop_cannot_start_another_request(self):
        with self.assertRaisesRegex(RuntimeError, 'cleanup failed'):
            self.execute([self.response(503)], cleanup_error=RuntimeError('cleanup failed'))
        self.assertEqual(self.runtime.test_setup.api_request.call_count, 1)
        with self.assertRaises(TestSuiteStopped):
            self.execute([self.response(503)], stopped=True)
        self.assertEqual(self.runtime.test_setup.api_request.call_count, 1)
