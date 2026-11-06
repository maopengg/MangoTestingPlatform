from contextlib import contextmanager
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.db import OperationalError
from django.test import SimpleTestCase
from mangotools.enums import TaskEnum

from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.services.execution_result import ExecutionResultService
from src.apps.test_center.services.test_suite.detail_result import TestSuiteExecutionResultService
from src.apps.test_center.services.test_suite.infrastructure import TestSuiteInfrastructureService
from src.apps.test_center.services.test_suite.update_test_suite import UpdateTestSuite


class ResultWriteTransactionTests(SimpleTestCase):
    def setUp(self):
        self.connection = SimpleNamespace(in_atomic_block=False)
        self.store = {'status': TaskEnum.PROCEED.value, 'rows': 0, 'summary': None}
        self.rollbacks = 0
        self.atomic_calls = 0
        self.enter_patch(patch(
            'src.apps.test_center.services.execution_result.transaction.get_connection',
            return_value=self.connection,
        ))
        self.enter_patch(patch(
            'src.apps.test_center.services.execution_result.transaction.atomic', side_effect=self.atomic,
        ))
        self.sleep = self.enter_patch(patch('src.apps.test_center.services.execution_result.time.sleep'))

    def enter_patch(self, patcher):
        result = patcher.start()
        self.addCleanup(patcher.stop)
        return result

    @contextmanager
    def atomic(self):
        self.atomic_calls += 1
        previous = self.connection.in_atomic_block
        before = deepcopy(self.store)
        self.connection.in_atomic_block = True
        try:
            yield
        except Exception:
            self.store.clear()
            self.store.update(before)
            self.rollbacks += 1
            raise
        finally:
            self.connection.in_atomic_block = previous

    def assert_outside_transaction(self, _delay):
        self.assertFalse(self.connection.in_atomic_block)

    def test_retries_only_known_lock_errors_after_rollback(self):
        for code in (1205, 1213):
            with self.subTest(code=code):
                operation = Mock(side_effect=[OperationalError(code, 'lock conflict'), 'saved'])
                self.sleep.side_effect = self.assert_outside_transaction
                before = self.rollbacks
                self.assertEqual(ExecutionResultService.run_write_transaction(operation), 'saved')
                self.assertEqual(operation.call_count, 2)
                self.assertEqual(self.rollbacks, before + 1)

    def test_retry_exhaustion_rolls_back_and_raises_original_error(self):
        error = OperationalError(1205, 'lock conflict')

        def operation():
            self.store['status'] = 1
            self.store['rows'] += 1
            raise error

        with self.assertRaises(OperationalError) as raised:
            ExecutionResultService.run_write_transaction(operation)
        self.assertIs(raised.exception, error)
        self.assertEqual(self.atomic_calls, 3)
        self.assertEqual(self.sleep.call_count, 2)
        self.assertEqual(self.store, {'status': TaskEnum.PROCEED.value, 'rows': 0, 'summary': None})

    def test_other_operational_errors_are_not_retried(self):
        operation = Mock(side_effect=OperationalError(2003, 'connection failed'))
        with self.assertRaises(OperationalError):
            ExecutionResultService.run_write_transaction(operation)
        operation.assert_called_once()
        self.sleep.assert_not_called()

    def test_nested_transaction_propagates_to_owner_without_local_retry(self):
        self.connection.in_atomic_block = True
        operation = Mock(side_effect=OperationalError(1213, 'deadlock'))
        with self.assertRaises(OperationalError):
            ExecutionResultService.run_write_transaction(operation)
        operation.assert_called_once()
        self.assertEqual(self.atomic_calls, 0)
        self.sleep.assert_not_called()

    def test_file_is_prepared_once_before_any_transaction_and_reused_on_retry(self):
        payload = {'result_data': None, 'result_object_key': 'result/example.json',
                   'result_file_name': 'example.json', 'result_size': 10, 'result_checksum': 'checksum'}

        def prepare(*_args):
            self.assertFalse(self.connection.in_atomic_block)
            return payload

        with patch.object(ExecutionResultService, 'prepare_result_payload', side_effect=prepare) as upload, \
                patch.object(ExecutionResultService, '_save_result_record', side_effect=[
                    OperationalError(1205, 'lock conflict'), SimpleNamespace(id=7),
                ]) as write:
            result = ExecutionResultService.save_result(
                source_type='report', target_type='api_case', target_id=1, result_data=[],
            )
        self.assertEqual(result.id, 7)
        upload.assert_called_once()
        self.assertEqual(write.call_count, 2)
        for call in write.call_args_list:
            self.assertEqual(call.args[0]['result_object_key'], 'result/example.json')

    def test_single_writer_locks_suite_then_detail_and_updates_latest_only_once(self):
        order = []
        fields = {'test_suite_id': 2, 'test_suite_detail_id': 3, 'target_type': 'ui_case'}
        with patch('src.apps.test_center.services.execution_result.TestSuite.objects') as suites, \
                patch('src.apps.test_center.services.execution_result.TestSuiteDetails.objects') as details, \
                patch('src.apps.test_center.services.execution_result.ExecutionResult.objects') as results:
            suites.select_for_update.return_value.get.side_effect = lambda **_: order.append('suite')
            details.select_for_update.return_value.get.side_effect = lambda **_: order.append('detail')
            results.filter.return_value.update.side_effect = lambda **_: order.append('latest')
            results.filter.return_value.order_by.return_value.values_list.return_value.first.return_value = 4
            ExecutionResultService._save_result_record(fields, {'test_suite_detail_id': 3})
        self.assertEqual(order, ['suite', 'detail', 'latest'])
        results.filter.return_value.update.assert_called_once_with(is_latest=False)
        self.assertEqual(results.create.call_args.kwargs['attempt_no'], 5)

    def callback_context(self, case_type=TestCaseTypeEnum.API):
        detail = SimpleNamespace(
            id=3, test_suite_id=2, case_id=1, type=case_type.value, test_env=0,
            api_case_revision_id=None, api_case_release_id=None, status=TaskEnum.PROCEED.value,
            error_message=None, case_name='case', summary_data=None, retry=1,
        )

        def save(**_kwargs):
            self.assertTrue(self.connection.in_atomic_block)
            self.store['status'] = detail.status
            self.store['summary'] = detail.summary_data

        detail.save = Mock(side_effect=save)
        suite = SimpleNamespace(status=TaskEnum.PROCEED.value, retained_summary=None)
        self.suite_manager = self.enter_patch(patch(
            'src.apps.test_center.services.test_suite.update_test_suite.TestSuite.objects',
        ))
        self.suite_manager.select_for_update.return_value.get.return_value = suite
        details = self.enter_patch(patch(
            'src.apps.test_center.services.test_suite.update_test_suite.TestSuiteDetails.objects',
        ))
        details.get.return_value = detail
        details.select_for_update.return_value.get.return_value = detail
        details.select_for_update.return_value.filter.return_value.first.return_value = detail
        details.filter.return_value.exists.return_value = True
        self.enter_patch(patch(
            'src.apps.test_center.services.test_suite.update_test_suite.TestSuiteTimeoutRecoveryService.'
            'is_timeout_terminated', return_value=False,
        ))
        self.counter = self.enter_patch(patch(
            'src.apps.test_center.services.test_suite.update_test_suite.TestCounter.res_main',
        ))
        self.ui_write = self.enter_patch(patch(
            'src.apps.test_center.services.test_suite.update_test_suite.TestReportWriting.update_test_case',
        ))
        self.pytest_write = self.enter_patch(patch(
            'src.apps.test_center.services.test_suite.update_test_suite.PtestTestReportWriting.update_pytest_test_case',
        ))
        payload = {'result_data': None, 'result_object_key': 'result/example.json',
                   'result_file_name': 'example.json', 'result_size': 10, 'result_checksum': 'checksum'}

        def prepare(*_args):
            self.assertFalse(self.connection.in_atomic_block)
            return payload

        self.upload = self.enter_patch(patch.object(
            ExecutionResultService, 'prepare_result_payload', side_effect=prepare,
        ))
        execution = SimpleNamespace(
            steps=[SimpleNamespace(model_dump=lambda: {'id': 1, 'status': 1})],
            result_data=[{'status': 1}], name='case', source_snapshot={'version': 1},
        )
        return SimpleNamespace(
            id=3, test_suite=2, type=case_type, status=1, error_message=None,
            result_data=execution, model_dump_json=lambda: '{}',
        )

    def test_callback_retries_database_only_and_commits_state_with_result(self):
        data = self.callback_context()
        calls = []

        def write(*_args):
            self.assertTrue(self.connection.in_atomic_block)
            calls.append(self.store['status'])
            if len(calls) == 1:
                raise OperationalError(1205, 'lock conflict')
            self.store['rows'] += 1
            return SimpleNamespace(id=7)

        with patch.object(ExecutionResultService, '_save_result_record', side_effect=write):
            self.assertTrue(UpdateTestSuite.update_test_suite_details(data))
        self.assertEqual(calls, [1, 1])
        self.assertEqual(self.store['status'], 1)
        self.assertEqual(self.store['rows'], 1)
        self.assertIsNotNone(self.store['summary'])
        self.upload.assert_called_once()
        self.counter.assert_called_once_with(3)
        self.ui_write.assert_not_called()
        self.pytest_write.assert_not_called()

    def test_callback_failure_does_not_commit_success_or_summary(self):
        data = self.callback_context()
        with patch.object(ExecutionResultService, '_save_result_record', side_effect=OperationalError(1205, 'lock')):
            with self.assertRaises(OperationalError):
                UpdateTestSuite.update_test_suite_details(data)
        self.assertEqual(self.store, {'status': TaskEnum.PROCEED.value, 'rows': 0, 'summary': None})
        self.upload.assert_called_once()
        self.counter.assert_not_called()

    def test_stopped_report_does_not_accept_late_result(self):
        data = self.callback_context()
        self.suite_manager.select_for_update.return_value.get.return_value.status = TaskEnum.STOPPED.value
        with patch.object(ExecutionResultService, '_save_result_record') as write:
            self.assertFalse(UpdateTestSuite.update_test_suite_details(data))
        write.assert_not_called()
        self.counter.assert_not_called()

    def test_ui_and_pytest_callbacks_keep_projection_outside_retry_transaction(self):
        for case_type in (TestCaseTypeEnum.UI, TestCaseTypeEnum.PYTEST):
            with self.subTest(case_type=case_type):
                data = self.callback_context(case_type)

                def project(_result):
                    self.assertFalse(self.connection.in_atomic_block)

                self.ui_write.side_effect = project
                self.pytest_write.side_effect = project
                with patch.object(ExecutionResultService, '_save_result_record', return_value=SimpleNamespace(id=7)) as write:
                    self.assertTrue(UpdateTestSuite.update_test_suite_details(data))
                fields = write.call_args.args[0]
                if case_type == TestCaseTypeEnum.PYTEST:
                    self.assertEqual(fields['source_snapshot'], {'version': 1})
                    self.pytest_write.assert_called_once()
                    self.ui_write.assert_not_called()
                else:
                    self.assertIsNone(fields['source_snapshot'])
                    self.ui_write.assert_called_once()
                    self.pytest_write.assert_not_called()

    def test_snapshot_and_final_result_share_a_single_latest_writer(self):
        self.callback_context()
        detail = SimpleNamespace(
            id=3, test_suite_id=2, case_id=1, type=TestCaseTypeEnum.API.value, test_env=0,
            api_case_revision_id=None, api_case_release_id=None, status=TaskEnum.PROCEED.value, error_message=None,
            save=Mock(), retry=1,
        )
        snapshot = {'result_mode': 'snapshot', 'status': 'running', 'steps': [{'id': 1, 'status': 1}]}
        with patch.object(ExecutionResultService, '_save_result_record', return_value=SimpleNamespace(id=7)) as write:
            TestSuiteExecutionResultService.save_snapshot(detail, snapshot)
        write.assert_called_once()
        self.upload.assert_called_once()
        self.assertEqual(detail.summary_data['meta']['snapshot_status'], 'running')

    def test_counter_conflict_rolls_back_result_before_retry(self):
        data = self.callback_context()
        self.counter.side_effect = [OperationalError(1205, 'lock'), None]

        def write(*_args):
            self.store['rows'] += 1
            return SimpleNamespace(id=7)

        with patch.object(ExecutionResultService, '_save_result_record', side_effect=write):
            self.assertTrue(UpdateTestSuite.update_test_suite_details(data))
        self.assertEqual(self.store['rows'], 1)
        self.assertEqual(self.store['status'], 1)
        self.assertEqual(self.counter.call_count, 2)
        self.upload.assert_called_once()
