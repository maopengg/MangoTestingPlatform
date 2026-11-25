from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from mangotools.enums import StatusEnum, TaskEnum

from src.apps.auto_api.exceptions import AutoApiError, TestSuiteStopped
from src.apps.auto_api.schemas.recovery import ApiStepExecutionConfig, is_recovery_step
from src.apps.auto_api.services.execution.cases.test_case import TestCase
from src.apps.auto_api.models import ApiCaseDetailed
from src.apps.auto_api.services.api_case.snapshot import ApiExecutableSnapshotService
from src.apps.auto_api.services.api_case.step import ApiCaseStepService
from src.apps.auto_api.api.serializers.api_case_detailed import ApiCaseDetailedSerializers
from src.apps.user.services.authorization.permission import PermissionMenuService
from src.interfaces.mcp.authentication import component_policy, permission_error
from src.apps.test_center.services.reporting.test_suite.detail_result import TestSuiteExecutionResultService


class ApiCaseRecoveryTests(SimpleTestCase):
    def step(self, step_id, recovery=False):
        return SimpleNamespace(
            id=step_id, case_sort=step_id,
            execution_config={'is_recovery': True} if recovery else {},
        )

    def runtime(self, steps, outcomes=None, cache=None):
        runtime = TestCase.__new__(TestCase)
        runtime.case_id = 847
        runtime.test_suite = None
        runtime.api_case_result = SimpleNamespace(
            main_status=None, recovery_status=None, recovery_errors=[], steps=[],
        )
        runtime.get_case_detailed_queryset = Mock(return_value=steps)
        runtime.case_base = Mock()
        runtime.test_setup = Mock()
        runtime.test_setup.test_data.get_all.return_value = {'original': 'package2'} if cache is None else cache
        runtime.test_setup.test_data.get_data_factory_all.return_value = {}
        runtime.trace_recorder = Mock()
        runtime.trace_recorder.execution_scope.return_value = nullcontext()
        runtime.save_case_detailed_runtime_state = Mock()
        runtime.build_step_execution_context = Mock(return_value={})
        runtime.get_case_detailed_name = lambda step: str(step.id)
        runtime.format_case_detailed_failure_message = lambda _: '主流程失败'
        runtime.format_case_detailed_warning_message = lambda _: '主流程警告'
        runtime.write_following_case_detailed_warning_results = Mock(return_value=[])
        runtime.order = []
        outcomes = outcomes or {}

        def run(step, _=None):
            runtime.order.append(step.id)
            result = SimpleNamespace(is_recovery=is_recovery_step(step), status=1)
            runtime.api_case_result.steps.append(result)
            outcome = outcomes.get(step.id)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        runtime.detailed_parameter = Mock(side_effect=run)
        return runtime

    def lifecycle_runtime(self, steps, outcomes=None, cache=None):
        runtime = self.runtime(steps, outcomes, cache)
        runtime.api_case = SimpleNamespace(
            id=847, name='恢复验证', project_product_id=1, front_public=[], front_auth_config=[],
            front_custom=[], front_sql=[], front_headers=[], parametrize=[], posterior_sql=[], status=0,
        )
        runtime.test_env = 1
        runtime.test_suite_details = None
        runtime.api_case_result.status = 0
        runtime.api_case_result.error_message = None
        runtime.api_case_result.model_dump_json = lambda: '{}'
        runtime.update_test_case_detailed_proceed = Mock()
        runtime.update_test_case_detailed_unfinished = Mock()
        runtime.update_test_case = Mock()
        runtime.apply_gray_with_trace = Mock(return_value=[])
        runtime.restore_gray_with_trace = Mock()
        return runtime

    def test_success_runs_recovery_only_after_main(self):
        runtime = self.runtime([self.step(1), self.step(2, True), self.step(3)])
        self.assertIsNone(runtime.case_detailed(847, None))
        self.assertEqual(runtime.order, [1, 3, 2])
        self.assertEqual(runtime.api_case_result.main_status, 1)
        self.assertEqual(runtime.api_case_result.recovery_status, 1)

    def test_failure_skips_normal_steps_but_runs_recovery(self):
        runtime = self.runtime([self.step(1), self.step(2), self.step(3, True)], {1: (0, '失败')})
        self.assertEqual(runtime.case_detailed(847, None)[0], 0)
        self.assertEqual(runtime.order, [1, 3])
        self.assertEqual(runtime.api_case_result.main_status, 0)
        self.assertEqual(runtime.api_case_result.recovery_status, 1)

    def test_http_failure_and_retry_exhaustion_still_run_final_recovery(self):
        from src.apps.auto_api.enums import ApiBodyTypeEnum, ApiProtocolTypeEnum, MethodEnum
        from src.apps.auto_api.enums.assertion import ApiDefaultAssertionCheck
        from src.apps.auto_api.schemas.execution import ApiExecutionResponse
        from src.apps.auto_api.services.execution.cases.test_case_parts.parameter import ApiTestCaseParameterMixin

        path = 'src.apps.auto_api.services.execution.cases.test_case_parts.parameter'
        for retries in (1, 2):
            for frozen in (False, True):
                with self.subTest(retries=retries, frozen=frozen):
                    main, skipped, recovery = self.step(1), self.step(2), self.step(3, True)
                    runtime = self.runtime([main, skipped, recovery])
                    api = SimpleNamespace(id=7, project_product_id=1, name='测试请求', method=MethodEnum.POST.value,
                                          protocol_type=ApiProtocolTypeEnum.HTTP.value,
                                          body_type=ApiBodyTypeEnum.NONE.value, url='https://example.com/action')
                    for step in (main, skipped, recovery):
                        step.api_info, step.api_info_id = api, api.id
                    parameters = {step.id: SimpleNamespace(
                        id=step.id, name=f'场景{step.id}', error_retry=retries if step.id == 1 else 1,
                        retry_interval=0, params=None, body_config=None, sse_config=None, allow_failure=False,
                        front_sql=[], front_func=None, posterior_sql=[], posterior_func=None,
                        posterior_file={}, posterior_response=[], posterior_response_text=[],
                        ass_jsonpath=[], ass_general=[], ass_json_all={}, ass_text_all=None, ass_schema=None,
                    ) for step in (main, skipped, recovery)}
                    runtime.revision_aggregate = Mock() if frozen else None
                    runtime.is_step_debug = False
                    runtime.test_env, runtime.user_id = 0, 1
                    runtime.api_case = SimpleNamespace(callback_checks=[], front_public=[], front_auth_config=[])
                    runtime.api_case_result.callback_results = []
                    runtime.current_step_execution_context = None
                    runtime.build_step_execution_context.return_value = None
                    runtime.trace_recorder.start_step.side_effect = lambda *args, **kwargs: SimpleNamespace(id=1, status=3)
                    runtime.get_parameters_for_step = Mock(side_effect=lambda step: [parameters[step.id]])
                    runtime.resolve_protocol_expectation = Mock(return_value=([], False))
                    runtime.has_user_configured_assertions = Mock(return_value=True)
                    runtime.resolve_scenario_result_name = lambda parameter, step: parameter.name
                    runtime.update_test_case_detailed_parameter = Mock()
                    runtime.test_setup.api_request.side_effect = [
                        *[ApiExecutionResponse(code=500, headers={}, time=0.1, json=None) for _ in range(retries)],
                        ApiExecutionResponse(code=200, headers={}, time=0.1, json={}),
                    ]
                    runtime.detailed_parameter = ApiTestCaseParameterMixin.detailed_parameter.__get__(runtime)
                    with patch(path + '.ParameterDataFactory') as factory, patch(path + '.CaseParameter') as scenario, \
                            patch(path + '.ApiCaseStepService.resolve_step_api_runtime', return_value=api), \
                            patch(path + '.ProtocolCallOutcomeService.default_checks', return_value=frozenset(ApiDefaultAssertionCheck)):
                        factory.return_value.runner.execution_ids = []
                        scenario.return_value.headers.return_value = {}
                        scenario.return_value.front_main.side_effect = lambda request: request
                        scenario.return_value.posterior_main.side_effect = lambda response: response
                        scenario.return_value.ass_main.return_value = ([], StatusEnum.SUCCESS.value, None)
                        result = runtime.case_detailed(847, None)
                    self.assertEqual(result[0], StatusEnum.FAIL.value)
                    self.assertEqual(runtime.api_case_result.main_status, StatusEnum.FAIL.value)
                    self.assertEqual(runtime.api_case_result.recovery_status, StatusEnum.SUCCESS.value)
                    self.assertEqual([item.id for item in runtime.api_case_result.steps], [1] * retries + [3])
                    self.assertTrue(runtime.api_case_result.steps[-1].is_recovery)
                    scenario.return_value.posterior_main.assert_called_once()
                    scenario.return_value.ass_main.assert_called_once()
                    self.assertEqual(factory.return_value.cleanup.call_count, retries + 1)

    def test_unexpected_exception_still_runs_recovery_and_propagates(self):
        runtime = self.runtime([self.step(1), self.step(2, True)], {1: RuntimeError('failure')})
        with self.assertRaises(RuntimeError):
            runtime.case_detailed(847, None)
        self.assertEqual(runtime.order, [1, 2])

    def test_stop_still_runs_recovery(self):
        runtime = self.runtime([self.step(1), self.step(2, True)], {1: TestSuiteStopped()})
        with self.assertRaises(TestSuiteStopped):
            runtime.case_detailed(847, None)
        self.assertEqual(runtime.order, [1, 2])
        self.assertEqual(runtime.api_case_result.main_status, TaskEnum.STOPPED.value)

    def test_recovery_failure_fails_case_but_attempts_all_recovery(self):
        runtime = self.runtime([
            self.step(1), self.step(2, True), self.step(3, True), self.step(4, True),
        ], {2: (0, '恢复失败')})
        self.assertEqual(runtime.case_detailed(847, None)[0], StatusEnum.FAIL.value)
        self.assertEqual(runtime.order, [1, 2, 3, 4])
        self.assertEqual(runtime.api_case_result.main_status, 1)
        self.assertEqual(runtime.api_case_result.recovery_status, 0)
        self.assertEqual(len(runtime.api_case_result.recovery_errors), 1)

    def test_empty_cache_does_not_skip_restore(self):
        runtime = self.runtime([self.step(1), self.step(2, True)], cache={})
        self.assertIsNone(runtime.case_detailed(847, None))
        self.assertEqual(runtime.order, [1, 2])
        self.assertEqual(runtime.api_case_result.recovery_errors, [])

    def test_false_and_zero_are_valid_original_values(self):
        runtime = self.runtime([self.step(1, True)], cache={'enabled': False, 'count': 0})
        self.assertIsNone(runtime.case_detailed(847, None))
        self.assertEqual(runtime.order, [1])

    def test_recovery_exception_does_not_abort_independent_restore(self):
        runtime = self.runtime([self.step(1, True), self.step(2, True)], {1: RuntimeError('failure')})
        self.assertEqual(runtime.case_detailed(847, None)[0], 0)
        self.assertEqual(runtime.order, [1, 2])
        self.assertFalse(runtime._running_recovery)

    def test_parameterized_iteration_does_not_implicitly_delete_variables(self):
        runtime = self.runtime([self.step(1), self.step(2, True)])
        runtime.case_detailed(847, None)
        runtime.case_detailed(847, None)
        runtime.test_setup.test_data.delete_cache.assert_not_called()

    def test_partial_run_still_recovers_steps_after_cutoff(self):
        runtime = self.runtime([])
        runtime.get_case_detailed_queryset.side_effect = [[self.step(1)], [self.step(1), self.step(2, True)]]
        runtime.case_detailed(847, 1)
        self.assertEqual(runtime.order, [1, 2])

    def test_configuration_only_accepts_boolean_switch(self):
        self.assertFalse(ApiStepExecutionConfig.parse_config({}).is_recovery)
        self.assertTrue(ApiStepExecutionConfig.parse_config({'is_recovery': True}).is_recovery)
        self.assertEqual(ApiStepExecutionConfig.parse_config({'is_recovery': False}).model_dump(exclude_defaults=True), {})
        for value in ({'extra': True}, {'is_recovery': 'true'}, {'is_recovery': 1}, [], None):
            with self.subTest(value=value), self.assertRaises(AutoApiError):
                ApiStepExecutionConfig.parse_config(value)

    def test_previous_iteration_recovery_error_does_not_fail_later_iteration(self):
        outcomes = {2: (0, '首次恢复失败')}
        runtime = self.runtime([self.step(1), self.step(2, True)], outcomes)
        self.assertEqual(runtime.case_detailed(847, None)[0], 0)
        outcomes.clear()
        self.assertIsNone(runtime.case_detailed(847, None))
        self.assertEqual(runtime.api_case_result.recovery_status, 0)
        self.assertEqual(len(runtime.api_case_result.recovery_errors), 1)

    def test_switch_updates_only_execution_config(self):
        step = SimpleNamespace(id=2, case_id=1, save=Mock())
        with patch('src.apps.auto_api.services.api_case.step.ApiCaseDetailed.objects') as objects, \
                patch('src.apps.auto_api.services.api_case.step.ApiCaseAggregateMutationService.mutate') as mutate:
            objects.filter.return_value.first.return_value = step
            mutate.side_effect = lambda _, **kwargs: kwargs['operation'](None)
            for config, expected in (({'is_recovery': True}, {'is_recovery': True}), ({}, {})):
                result = ApiCaseStepService.configure_recovery(2, config, operator_id=4)
                self.assertEqual(step.execution_config, expected)
                self.assertEqual(result['execution_config'], expected)
                step.save.assert_called_with(update_fields=['execution_config', 'update_user', 'update_time'])

    def test_serializer_validates_json_contract(self):
        serializer = ApiCaseDetailedSerializers()
        self.assertEqual(serializer.validate_execution_config({'is_recovery': False}), {})
        with self.assertRaises(AutoApiError):
            serializer.validate_execution_config({'unknown_option': True})

    def test_report_summary_preserves_phase_results(self):
        summary = TestSuiteExecutionResultService.build_api_step_summary({
            'id': 1, 'is_recovery': True, 'main_status': 1, 'recovery_status': 0,
            'recovery_errors': ['恢复失败'],
        })
        self.assertTrue(summary['is_recovery'])
        self.assertEqual(summary['main_status'], 1)
        self.assertEqual(summary['recovery_status'], 0)
        self.assertEqual(summary['recovery_errors'], ['恢复失败'])

    def test_snapshot_preserves_recovery_and_legacy_defaults(self):
        step = ApiCaseDetailed(id=1, case_id=1, api_info_id=1, execution_config={'is_recovery': True})
        payload = ApiExecutableSnapshotService.serialize_model(step, ApiExecutableSnapshotService.STEP_RUNTIME_FIELDS)
        restored = ApiExecutableSnapshotService.hydrate_model(ApiCaseDetailed, payload)
        self.assertEqual(restored.execution_config, {'is_recovery': True})
        legacy = ApiExecutableSnapshotService.hydrate_model(ApiCaseDetailed, {'id': 1})
        self.assertEqual(legacy.execution_config, {})

    def test_mcp_recovery_requires_edit_and_project_scope(self):
        policy = component_policy('update_api_case_step_recovery')
        self.assertEqual(policy.permission_key, 'api.case:change')
        self.assertTrue(policy.project_scoped)
        with patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=False), \
                patch.object(PermissionMenuService, 'permission_keys_for_user', return_value={'api.case'}):
            result = permission_error(SimpleNamespace(id=1), 'update_api_case_step_recovery', {'step_id': 1})
        self.assertIsNotNone(result)

    def test_lifecycle_recovery_failure_cannot_be_overwritten_by_success(self):
        runtime = self.lifecycle_runtime([self.step(1), self.step(2, True)], {2: (0, '恢复失败')})
        result = runtime.test_case()
        self.assertEqual(result.status, 0)
        self.assertEqual(result.main_status, 1)
        self.assertEqual(result.recovery_status, 0)
        runtime.case_base.case_posterior_main.assert_called_once()

    def test_lifecycle_front_exception_still_attempts_recovery(self):
        runtime = self.lifecycle_runtime([self.step(1), self.step(2, True)], cache={})
        runtime.case_base.case_front_main.side_effect = RuntimeError('front failure')
        result = runtime.test_case()
        self.assertEqual(result.status, 0)
        self.assertEqual(runtime.order, [2])
        self.assertEqual(result.recovery_status, 1)

    def test_lifecycle_stop_restores_then_closes_sessions(self):
        runtime = self.lifecycle_runtime([self.step(1), self.step(2, True)], {1: TestSuiteStopped()})
        result = runtime.test_case()
        self.assertEqual(runtime.order, [1, 2])
        self.assertEqual(result.status, TaskEnum.STOPPED.value)
        self.assertEqual(result.recovery_status, 1)
        runtime.test_setup.close_db_connections.assert_called_once()

    @patch('src.apps.data_factory.services.governance.infrastructure.DatasourceInfrastructureService.log_reference',
           return_value='safe-reference')
    def test_database_failure_and_failed_status_writes_do_not_skip_recovery(self, record_error):
        from django.db import InterfaceError
        from src.apps.test_center.enums.reporting import ReportRecoveryCauseEnum

        runtime = self.lifecycle_runtime([self.step(1), self.step(2, True)])
        runtime.test_setup.init_test_object.side_effect = InterfaceError(0, 'secret SQL')
        runtime.update_test_case.side_effect = InterfaceError(0, 'secret SQL')
        runtime.update_test_case_detailed_unfinished.side_effect = InterfaceError(0, 'secret SQL')
        runtime.run_resource_cleanup = Mock()
        result = runtime._test_case()
        self.assertEqual(runtime.order, [2])
        self.assertEqual(result.status, StatusEnum.FAIL.value)
        self.assertEqual(result.main_status, StatusEnum.FAIL.value)
        self.assertTrue(result.infrastructure_blocked)
        self.assertEqual(runtime.report_recovery_cause, ReportRecoveryCauseEnum.RESULT_UNAVAILABLE)
        from src.apps.test_center.enums.reporting import ReportRecoveryActionEnum
        from src.apps.test_center.services.reporting.test_suite.recovery import ReportRecoveryService
        self.assertEqual(ReportRecoveryService.decide(runtime.report_recovery_cause, []),
                         ReportRecoveryActionEnum.RECOVER)
        self.assertNotIn('secret SQL', result.error_message)
        runtime.case_base.case_front_main.assert_not_called()
        runtime.case_base.case_posterior_main.assert_called_once()
        runtime.run_resource_cleanup.assert_called()
        for name in ('close_mcp_sessions', 'close_grpc_channels', 'close_db_connections'):
            getattr(runtime.test_setup, name).assert_called_once()
        self.assertTrue(record_error.called)

    @patch('src.apps.data_factory.services.governance.infrastructure.DatasourceInfrastructureService.log_reference',
           return_value='safe-reference')
    def test_business_failure_with_failed_trace_and_status_still_attempts_recovery(self, _):
        from django.db import InterfaceError
        from src.apps.auto_api.exceptions import API_CASE_STEP_DEBUG_BUSY

        runtime = self.lifecycle_runtime([self.step(1), self.step(2, True)])
        runtime.case_base.case_front_main.side_effect = AutoApiError(API_CASE_STEP_DEBUG_BUSY)
        runtime.trace_recorder.fail_trace.side_effect = InterfaceError(0, '')
        runtime.update_test_case.side_effect = InterfaceError(0, '')
        result = runtime._test_case()
        self.assertEqual(runtime.order, [2])
        self.assertTrue(result.infrastructure_blocked)
        runtime.test_setup.close_db_connections.assert_called_once()

    @patch('src.apps.data_factory.services.governance.infrastructure.DatasourceInfrastructureService.log_reference',
           return_value='safe-reference')
    def test_recovery_lookup_failure_still_attempts_cleanup_and_closes_every_connection(self, _):
        from django.db import InterfaceError

        runtime = self.lifecycle_runtime([self.step(1), self.step(2, True)])
        runtime.test_setup.init_test_object.side_effect = InterfaceError(0, '')
        runtime.get_case_detailed_queryset.side_effect = InterfaceError(0, '')
        runtime.run_resource_cleanup = Mock(side_effect=RuntimeError('secret cleanup'))
        runtime.test_setup.close_mcp_sessions.side_effect = RuntimeError('secret connection')
        with self.assertRaises(InterfaceError):
            runtime._test_case()
        runtime.run_resource_cleanup.assert_called_once()
        runtime.test_setup.close_mcp_sessions.assert_called_once()
        runtime.test_setup.close_grpc_channels.assert_called_once()
        runtime.test_setup.close_db_connections.assert_called_once()
        self.assertTrue(runtime.api_case_result.infrastructure_blocked)
        self.assertNotIn('secret', runtime.api_case_result.error_message)

    def test_exception_in_main_keeps_original_error_and_recovery_error(self):
        runtime = self.lifecycle_runtime([self.step(1), self.step(2, True)], {
            1: RuntimeError('main failure'), 2: (0, '恢复失败'),
        })
        result = runtime.test_case()
        self.assertEqual(result.status, 0)
        self.assertIn('平台内部异常', result.error_message)
        self.assertNotIn('main failure', result.error_message)
        self.assertIn('恢复失败', result.error_message)

    def test_report_block_receives_original_failure_and_recovery_evidence(self):
        runtime = self.lifecycle_runtime([self.step(1), self.step(2, True)], {
            1: RuntimeError('private internal detail'), 2: (0, '恢复失败'),
        })
        runtime.test_suite_details = 77
        runtime.api_case_result.model_dump = lambda: {'steps': [], 'recovery_errors': ['恢复失败']}
        with patch('src.apps.data_factory.services.cleanup.cleanup_schedule.DataFactoryCleanupScheduleService.current_owner',
                   return_value={'parent_attempt': 1}), \
                patch('src.apps.test_center.services.reporting.test_suite.infrastructure.TestSuiteInfrastructureService.block',
                      return_value=True) as block, \
                patch('src.apps.data_factory.services.governance.infrastructure.DatasourceInfrastructureService.log_reference',
                      return_value='safe-reference'):
            result = runtime.test_case()
        reason = block.call_args.kwargs['interruption_reason']
        self.assertIn('safe-reference', reason)
        self.assertIn('恢复失败', reason)
        self.assertNotIn('private internal detail', reason)
        self.assertEqual(result.error_message, reason)

    def test_stopped_report_only_saves_evidence_without_changing_status(self):
        suite = SimpleNamespace(status=TaskEnum.STOPPED.value, retained_summary=None)
        detail = SimpleNamespace(status=TaskEnum.STOPPED.value, id=1, test_suite_id=1, case_id=1, type=1)
        result = SimpleNamespace(steps=[SimpleNamespace(model_dump=lambda: {'is_recovery': True})])
        with patch('src.apps.test_center.services.reporting.test_suite.detail_result.TestSuite.objects') as suites, \
                patch('src.apps.test_center.services.reporting.test_suite.detail_result.TestSuiteDetails.objects') as details, \
                patch.object(TestSuiteExecutionResultService, 'save_result') as save, \
                patch('src.apps.test_center.services.reporting.test_suite.detail_result.ExecutionResultService.'
                      'prepare_result_payload', return_value={}) as prepare, \
                patch('src.apps.test_center.services.reporting.test_suite.detail_result.ExecutionResultService.'
                      'run_write_transaction', side_effect=lambda operation: operation()):
            suites.select_for_update.return_value.get.return_value = suite
            details.get.return_value = detail
            details.select_for_update.return_value.get.return_value = detail
            TestSuiteExecutionResultService.save_stopped_api_recovery(1, result)
        save.assert_called_once_with(detail, [{'is_recovery': True}], prepared_result_payload={})
        prepare.assert_called_once()
        self.assertEqual(detail.status, TaskEnum.STOPPED.value)
        self.assertEqual(suite.status, TaskEnum.STOPPED.value)
