from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from mangotools.enums import TaskEnum

from src.apps.data_factory.exceptions import DataFactoryError, DATASOURCE_GOVERNOR_UNAVAILABLE, DATASOURCE_SETTLEMENT_FAILED
from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService


class ApiInfrastructureTests(SimpleTestCase):
    def runtime(self):
        from src.apps.auto_api.tests.test_api_case_recovery import ApiCaseRecoveryTests
        helper = ApiCaseRecoveryTests('test_success_runs_recovery_only_after_main')
        return helper.lifecycle_runtime([helper.step(1), helper.step(2, True)])

    def test_platform_front_failure_is_incomplete_not_business_failure_and_cleanup_runs(self):
        runtime = self.runtime()
        runtime.case_base.case_front_main.side_effect = DataFactoryError(DATASOURCE_GOVERNOR_UNAVAILABLE)
        result = runtime.test_case()
        self.assertTrue(result.infrastructure_blocked)
        self.assertEqual(result.status, TaskEnum.INFRASTRUCTURE_BLOCKED.value)
        runtime.update_test_case.assert_called_with(runtime.case_id, TaskEnum.FAIL.value)
        runtime.update_test_case_detailed_unfinished.assert_not_called()
        runtime.case_base.case_posterior_main.assert_called_once()
        runtime.test_setup.close_db_connections.assert_called_once()
        runtime.trace_recorder.fail_trace.assert_called_with(result.error_message,
                                                           summary={'infrastructure_blocked': True})

    def test_reconciled_cleanup_finishes_success_without_masking_business_failure(self):
        from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService as Infrastructure
        for status in (TaskEnum.SUCCESS.value, TaskEnum.FAIL.value):
            runtime = self.runtime()
            def cleanup():
                error = TimeoutError()
                error._datasource_audit_request_id = 'AUTO_DELETE'
                Infrastructure.capture(error, result_unknown=True)
                Infrastructure.resolve_verified_requests(['AUTO_DELETE'])
                runtime.api_case_result.status = status
            runtime.case_base.case_posterior_main.side_effect = cleanup
            result = runtime.test_case()
            self.assertEqual(result.status, status)
            self.assertFalse(getattr(result, 'infrastructure_blocked', False))
            if status == TaskEnum.SUCCESS.value:
                runtime.trace_recorder.finish_trace.assert_called_once()
            else:
                runtime.trace_recorder.fail_trace.assert_called_once()

    def test_business_success_with_unsettled_cleanup_is_not_reported_pass_or_fail(self):
        runtime = self.runtime()
        runtime.case_base.case_posterior_main.side_effect = DataFactoryError(DATASOURCE_SETTLEMENT_FAILED)
        result = runtime.test_case()
        self.assertEqual(result.main_status, TaskEnum.SUCCESS.value)
        self.assertEqual(result.status, TaskEnum.INFRASTRUCTURE_BLOCKED.value)
        self.assertTrue(result.infrastructure_blocked)
        runtime.case_base.case_posterior_main.assert_called_once()

    def test_platform_cleanup_faults_and_unsupported_cost_never_become_business_failure(self):
        from src.apps.data_factory.exceptions import (
            DATA_FACTORY_CLEANUP_TIMEOUT, DATA_FACTORY_CLEANUP_COORDINATION_FAILED,
            DATA_FACTORY_CLEANUP_IN_PROGRESS, DATASOURCE_OPERATION_COST_EXCEEDED,
            DATASOURCE_ADMISSION_TIMEOUT, DATASOURCE_AUDIT_REQUEST_CONFLICT, DATASOURCE_AUDIT_RESULT_UNAVAILABLE,
        )
        for definition, values in ((DATA_FACTORY_CLEANUP_TIMEOUT, None), (DATA_FACTORY_CLEANUP_IN_PROGRESS, None),
                                   (DATA_FACTORY_CLEANUP_COORDINATION_FAILED, ('AUTO coordination',)),
                                   (DATASOURCE_OPERATION_COST_EXCEEDED, ('AUTO response too large',)),
                                   (DATASOURCE_ADMISSION_TIMEOUT, None), (DATASOURCE_AUDIT_REQUEST_CONFLICT, None),
                                   (DATASOURCE_AUDIT_RESULT_UNAVAILABLE, None)):
            with self.subTest(code=definition.code):
                runtime = self.runtime()
                runtime.case_base.case_posterior_main.side_effect = DataFactoryError(
                    definition, **({'value': values} if values else {}))
                result = runtime.test_case()
                self.assertEqual(result.main_status, TaskEnum.SUCCESS.value)
                self.assertEqual(result.status, TaskEnum.INFRASTRUCTURE_BLOCKED.value)
                self.assertTrue(result.infrastructure_blocked)
                runtime.case_base.case_posterior_main.assert_called_once()

    def test_genuine_es_cleanup_verification_failure_is_not_hidden_as_platform_fault(self):
        from src.apps.data_factory.exceptions import DATA_FACTORY_ES_CLEANUP_TIMEOUT
        runtime = self.runtime()
        runtime.case_base.case_posterior_main.side_effect = DataFactoryError(DATA_FACTORY_ES_CLEANUP_TIMEOUT)
        result = runtime.test_case()
        self.assertEqual(result.main_status, TaskEnum.SUCCESS.value)
        self.assertEqual(result.status, TaskEnum.FAIL.value)
        self.assertFalse(getattr(result, 'infrastructure_blocked', False))

    def test_read_row_limit_in_post_custom_function_is_case_failure_with_direct_reason(self):
        from src.apps.auto_api.services.execution.base.api_base_test_setup import APIBaseTestSetup
        from src.apps.auto_api.exceptions import API_CASE_POST_FUNCTION_FAILED
        from src.apps.data_factory.services.governance.datasource_cost import DatasourceCostService
        setup = APIBaseTestSetup.__new__(APIBaseTestSetup)
        def sql(*args):
            DatasourceCostService.abort_result(Mock(), Mock(), limit=100, observed_rows=101)
        setup.analytic_func = Mock(return_value=sql)
        runtime = self.runtime()
        runtime.case_base.case_posterior_main.side_effect = lambda: setup.execute_analytic_func(
            'AUTO_fixture', error_msg=API_CASE_POST_FUNCTION_FAILED)
        result = runtime.test_case()
        self.assertEqual(result.main_status, TaskEnum.SUCCESS.value)
        self.assertEqual(result.status, TaskEnum.FAIL.value)
        self.assertFalse(getattr(result, 'infrastructure_blocked', False))
        self.assertIn('用例场景后置自定义函数执行失败', result.error_message)
        self.assertIn('并及时修改用例', result.error_message)
        self.assertIn('100 行', result.error_message)
        self.assertIn('至少 101 行', result.error_message)
        self.assertNotIn('平台安全执行边界', result.error_message)
        runtime.case_base.case_posterior_main.assert_called_once()
        runtime.test_setup.close_db_connections.assert_called_once()

    def test_business_step_does_not_continue_after_infrastructure_error_is_wrapped(self):
        runtime = self.runtime()
        def blocked(*args):
            DatasourceInfrastructureService.capture(DataFactoryError(DATASOURCE_GOVERNOR_UNAVAILABLE))
            return 0, 'wrapped platform error'
        runtime.detailed_parameter.side_effect = blocked
        with DatasourceInfrastructureService.scope():
            result = runtime.run_normal_steps([Mock(), Mock()])
        self.assertEqual(result[0], TaskEnum.PROCEED.value)
        runtime.detailed_parameter.assert_called_once()

    def test_business_request_never_calls_datasource_governor_or_backlog_gate(self):
        from types import SimpleNamespace
        from src.apps.auto_api.services.execution.base.api_base_test_setup.base_request import BaseRequest
        from src.apps.auto_api.schemas.execution import ApiExecutionRequest
        request = BaseRequest.__new__(BaseRequest)
        request.timeout, request.test_data = 30, None
        request.test_object = SimpleNamespace(environment=0, project_product_id=1)
        body = SimpleNamespace(request_body=None, request_files=None, content_type=None, close=Mock())
        request.send_request = Mock()
        with patch('src.apps.auto_api.services.execution.base.api_base_test_setup.base_request.prepare_request_body', return_value=body), \
                patch('src.apps.data_factory.services.governance.datasource_governor.DatasourceGovernorService.acquire',
                      side_effect=AssertionError('business request must not acquire SQL quota')), \
                patch('src.apps.data_factory.services.governance.datasource_governor.DatasourceGovernorService.policy',
                      side_effect=AssertionError('business request must not load SQL quota')):
            request.http(ApiExecutionRequest(method='GET', url='https://example.com'), 1)
        request.send_request.assert_called_once()
        body.close.assert_called_once()

    def test_hundred_business_requests_can_reach_transport_together_without_datasource_quota(self):
        import threading
        from concurrent.futures import ThreadPoolExecutor
        from types import SimpleNamespace
        from src.apps.auto_api.services.execution.base.api_base_test_setup.base_request import BaseRequest
        from src.apps.auto_api.schemas.execution import ApiExecutionRequest
        barrier = threading.Barrier(100)
        lock = threading.Lock()
        sent = []
        bodies = []
        def prepare(*args):
            body = SimpleNamespace(request_body=None, request_files=None, content_type=None, close=Mock())
            with lock:
                bodies.append(body)
            return body
        def transport(instance, request_data, prepared_body):
            with lock:
                sent.append(request_data.url)
            barrier.wait(timeout=10)
            return Mock()
        def execute(index):
            instance = BaseRequest.__new__(BaseRequest)
            instance.timeout, instance.test_data = 30, None
            return instance.http(ApiExecutionRequest(method='GET', url=f'https://example.com/{index}'), 1)
        with patch('src.apps.auto_api.services.execution.base.api_base_test_setup.base_request.prepare_request_body', side_effect=prepare), \
                patch.object(BaseRequest, 'send_request', transport), \
                patch('src.apps.data_factory.services.governance.datasource_governor.DatasourceGovernorService.policy',
                      side_effect=AssertionError('business request must not read datasource policy')), \
                ThreadPoolExecutor(max_workers=100) as pool:
            futures = [pool.submit(execute, index) for index in range(100)]
            for future in futures:
                future.result(timeout=15)
        self.assertEqual(len(set(sent)), 100)
        self.assertEqual(len(bodies), 100)
        for body in bodies:
            body.close.assert_called_once()

    def test_direct_debug_request_does_not_consult_datasource_policy(self):
        from types import SimpleNamespace
        from src.apps.auto_api.services.execution.base.api_base_test_setup.base_request import BaseRequest
        from src.apps.auto_api.schemas.execution import ApiExecutionRequest
        body = SimpleNamespace(request_body=None, request_files=None, content_type=None, close=Mock())
        with patch('src.apps.auto_api.services.execution.base.api_base_test_setup.base_request.prepare_request_body', return_value=body), \
                patch('src.apps.auto_api.services.execution.base.api_base_test_setup.base_request.HttpSseProtocolClient') as client, \
                patch('src.apps.data_factory.services.governance.datasource_governor.DatasourceGovernorService.policy',
                      side_effect=AssertionError('business debug must not read datasource policy')):
            BaseRequest.test_http(ApiExecutionRequest(method='GET', url='https://example.com'))
        client.return_value.test_request.assert_called_once()
        body.close.assert_called_once()
