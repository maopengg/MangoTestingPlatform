from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from src.apps.auto_ui.schemas.execution import UiCaseExecutionResult
from src.apps.auto_ui.services.test_report_writing import TestReportWriting
from src.apps.task_center.enums.execution import ExecutorTaskErrorCodeEnum
from src.apps.task_center.exceptions import TaskCenterError
from src.apps.task_center.services.execution.executor_task import ExecutorTaskService as Tasks
from src.apps.system.enums.executor import ExecutorTaskStatusEnum, ExecutorTaskTypeEnum


def ui_result():
    return {'id': 9, 'name': 'example', 'project_product_id': 1, 'project_product_name': 'example',
            'module_name': 'example', 'test_env': 0, 'status': 1, 'steps': [], 'execution_id': 'run-9',
            'data_factory_auto_cleanup_execution_ids': [7]}


class UiCleanupCompletionTests(SimpleTestCase):
    def setUp(self):
        self.task = SimpleNamespace(id=11, task_type=ExecutorTaskTypeEnum.UI_CASE.value, business_id=9,
                                    executor_user_id=4, retry_count=0, error_code=None,
                                    status=ExecutorTaskStatusEnum.RUNNING.value,
                                    payload={'func_args': {'id': 9, 'data_factory_auto_cleanup_execution_ids': [7]}})
        for path in ('src.apps.task_center.services.execution.executor_task.ExecutorTask.objects',
                     'src.apps.task_center.services.execution.executor_task.ExecutorTaskService._complete',
                     'src.apps.auto_ui.services.test_report_writing.TestReportWriting.prepare_factory_result'):
            guard = patch(path)
            mock = guard.start()
            self.addCleanup(guard.stop)
            if path.endswith('.objects'):
                self.objects = mock
                mock.filter.return_value.first.return_value = self.task
                mock.filter.return_value.update.return_value = 1
            elif path.endswith('._complete'):
                self.finish = mock
            else:
                self.prepare = mock
                mock.return_value = (ui_result(), [])

    def complete(self, result=None):
        return Tasks.complete(task_id=11, connection_id=None, username='executor', success=True,
                              result_data=result or ui_result())

    def test_cleanup_uses_server_dispatch_ids_before_atomic_projection(self):
        from src.apps.data_factory.services.cleanup_schedule import _parent_wait_pulse

        def prepare(result, expected):
            self.assertEqual(expected, [7])
            self.assertEqual(result['data_factory_auto_cleanup_execution_ids'], [7])
            _parent_wait_pulse.get()()
            return ui_result(), []

        self.prepare.side_effect = prepare
        self.complete({**ui_result(), 'data_factory_auto_cleanup_execution_ids': [999]})
        self.finish.assert_called_once()
        self.assertTrue(self.finish.call_args.kwargs['success'])
        self.assertTrue(any('expired_at__gt' in call.kwargs for call in self.objects.filter.call_args_list))
        self.assertNotIn('expired_at', self.objects.filter.return_value.update.call_args.kwargs)

    def test_cleanup_failure_is_persisted_as_failed_result_not_passed_case(self):
        result = {**ui_result(), 'status': 0, 'error_message': 'cleanup failed'}
        self.prepare.return_value = (result, ['cleanup failed'])
        self.complete()
        saved = self.finish.call_args.kwargs
        self.assertFalse(saved['success'])
        self.assertEqual(saved['error_code'], ExecutorTaskErrorCodeEnum.DATA_FACTORY_CLEANUP_FAILED.value)
        self.assertEqual(saved['result_data']['status'], 0)

    def test_repeated_original_success_does_not_overwrite_cleanup_failure(self):
        self.task.status = ExecutorTaskStatusEnum.FAILED.value
        self.task.error_code = ExecutorTaskErrorCodeEnum.DATA_FACTORY_CLEANUP_FAILED.value
        self.assertIs(self.complete(), self.task)
        self.prepare.assert_not_called()
        self.finish.assert_not_called()

    def test_foreign_case_result_cannot_start_cleanup(self):
        with self.assertRaises(TaskCenterError):
            self.complete({**ui_result(), 'id': 99})
        self.prepare.assert_not_called()

    @patch('src.apps.test_center.selectors.querysets.TestCenterQuerySelector.test_suite_details')
    def test_report_cleanup_uses_server_dispatch_report_not_client_claim(self, details):
        from src.apps.data_factory.services.cleanup_schedule import DataFactoryCleanupScheduleService
        self.task.payload['func_args'].update(test_suite_details=17, test_suite_id=99)
        details.return_value.filter.return_value.values.return_value.first.return_value = {'retry': 1}

        def prepare(result, expected):
            self.assertEqual(DataFactoryCleanupScheduleService.current_owner(),
                             {'parent_case_detail_id': 17, 'parent_attempt': 1})
            return ui_result(), []

        self.prepare.side_effect = prepare
        self.complete({**ui_result(), 'test_suite_details': 999})
        self.assertEqual(details.return_value.filter.call_args.kwargs['id'], 17)
        self.assertIsNone(DataFactoryCleanupScheduleService.current_owner())


class UiCleanupResultTests(SimpleTestCase):
    def test_platform_cleanup_fault_remains_incomplete_in_ui_result_and_report(self):
        from src.apps.data_factory.exceptions import DATA_FACTORY_CLEANUP_TIMEOUT, DataFactoryError
        from src.apps.data_factory.services.infrastructure import DatasourceInfrastructureService as Infrastructure
        from src.apps.data_factory.services.cleanup_schedule import DataFactoryCleanupScheduleService as Schedule
        def cleanup(data):
            Infrastructure.capture(DataFactoryError(DATA_FACTORY_CLEANUP_TIMEOUT))
            return ['AUTO cleanup blocked']
        with patch.object(TestReportWriting, 'cleanup_data_factory', side_effect=cleanup), \
                patch('src.apps.test_center.services.test_suite.infrastructure.TestSuiteInfrastructureService.block') as blocked:
            token = Schedule.set_owner(17, 2)
            try:
                result, failures = TestReportWriting.prepare_factory_result(ui_result(), [7])
            finally:
                Schedule.reset_owner(token)
        self.assertEqual(result['status'], 3)
        self.assertTrue(failures)
        self.assertEqual(blocked.call_args.args[:2], (17, 2))
        self.assertEqual(blocked.call_args.args[2][0].code, 34190)

    @patch.object(TestReportWriting, 'cleanup_data_factory', return_value=['cleanup failed'])
    def test_prepare_keeps_cleanup_ids_and_marks_failure(self, cleanup):
        result, failures = TestReportWriting.prepare_factory_result(ui_result(), [7])
        self.assertEqual(result['status'], 0)
        self.assertEqual(result['data_factory_auto_cleanup_execution_ids'], [7])
        self.assertTrue(failures)

    @patch('src.apps.auto_ui.services.test_report_writing.DataFactoryCleanup.cleanup_execution')
    def test_prepared_scope_does_not_repeat_io_inside_projection_transaction(self, cleanup):
        with TestReportWriting.prepared_cleanup_scope([7]):
            self.assertEqual(TestReportWriting.cleanup_data_factory(UiCaseExecutionResult(**ui_result())), [])
        cleanup.assert_not_called()
