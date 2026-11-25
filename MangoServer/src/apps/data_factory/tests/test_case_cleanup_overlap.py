from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from src.apps.data_factory.exceptions import DataFactoryError
from src.apps.data_factory.services.cleanup.cleanup_schedule import DataFactoryCleanupScheduleService as Schedule
from src.apps.data_factory.services.execution.case_config_runner import DataFactoryCaseConfigRunner


class CaseCleanupOverlapTests(SimpleTestCase):
    def setUp(self):
        self.runner = DataFactoryCaseConfigRunner(1, 12, 4, 0, Mock(), Mock(), user_id=4)
        self.runner.auto_cleanup_execution_ids = [7, 8, 9]

    def test_sql_order_is_preserved_but_all_observations_start_before_final_waits(self):
        events = []
        owner = {'parent_case_detail_id': 12, 'parent_attempt': 2}

        def enqueue(execution_id, **kwargs):
            events.append(('enqueue', execution_id))
            return SimpleNamespace(id=execution_id + 100)

        def cleanup(execution_id, **kwargs):
            events.append(('complete', execution_id))
            return {'fail': 0}

        with patch.object(Schedule, 'current_owner', return_value=owner), \
                patch('src.apps.data_factory.services.execution.case_config_runner.DataFactoryExecution.objects') as objects, \
                patch.object(Schedule, 'validate_report_owner') as validate, \
                patch.object(Schedule, 'enqueue', side_effect=enqueue), \
                patch.object(Schedule, 'wait', side_effect=lambda task_id, **kw: events.append(('sql', task_id))), \
                patch('src.apps.data_factory.services.execution.case_config_runner.DataFactoryCleanup.cleanup_execution',
                      side_effect=cleanup):
            objects.get.side_effect = lambda **kwargs: SimpleNamespace(id=kwargs['id'])
            self.runner.cleanup()
        self.assertEqual(events, [('enqueue', 7), ('sql', 107), ('enqueue', 8), ('sql', 108),
                                  ('enqueue', 9), ('sql', 109), ('complete', 7), ('complete', 8), ('complete', 9)])
        self.assertEqual(validate.call_count, 3)

    def test_no_report_keeps_inline_cleanup_and_never_enqueues(self):
        with patch.object(Schedule, 'current_owner', return_value=None), \
                patch.object(Schedule, 'enqueue') as enqueue, \
                patch('src.apps.data_factory.services.execution.case_config_runner.DataFactoryCleanup.cleanup_execution',
                      return_value={'fail': 0}) as cleanup:
            self.runner.cleanup()
        enqueue.assert_not_called()
        self.assertEqual(cleanup.call_count, 3)

    def test_stage_failure_still_checks_every_execution_and_cannot_become_success(self):
        with patch.object(Schedule, 'current_owner', return_value={'parent_case_detail_id': 12, 'parent_attempt': 2}), \
                patch('src.apps.data_factory.services.execution.case_config_runner.DataFactoryExecution.objects'), \
                patch.object(Schedule, 'validate_report_owner'), patch.object(Schedule, 'enqueue') as enqueue, \
                patch.object(Schedule, 'wait', side_effect=RuntimeError('AUTO_STAGE_FAILURE')), \
                patch('src.apps.data_factory.services.execution.case_config_runner.DataFactoryCleanup.cleanup_execution',
                      side_effect=[{'fail': 1, 'errors': [{'error': 'AUTO_SQL_NOT_VERIFIED'}]},
                                   {'fail': 0}, {'fail': 0}]) as cleanup:
            with self.assertRaises(DataFactoryError) as error:
                self.runner.cleanup()
        self.assertIn('AUTO_SQL_NOT_VERIFIED', error.exception.msg)
        self.assertEqual(enqueue.call_count, 1)
        self.assertEqual(cleanup.call_count, 3)


class CleanupSqlBoundaryTests(SimpleTestCase):
    def setUp(self):
        self.owner = patch.object(Schedule, 'current_owner', return_value=None)
        self.owner.start()
        self.addCleanup(self.owner.stop)

    def test_sql_done_is_only_an_ordering_barrier_not_cleanup_success(self):
        row = {'business_id': 7, 'status': 'pending', 'progress_data': {'sql_done': True}}
        with patch('src.apps.data_factory.services.cleanup.cleanup_schedule.TaskCenterQuerySelector.executor_tasks') as tasks, \
                patch.object(Schedule, 'verify_complete') as verify:
            tasks.return_value.filter.return_value.values.return_value.first.return_value = row
            Schedule.wait(17, sql_only=True)
        verify.assert_not_called()

    def test_final_wait_does_not_accept_sql_done_without_full_verification(self):
        rows = [
            {'business_id': 7, 'status': 'pending', 'progress_data': {'sql_done': True}},
            {'business_id': 7, 'status': 'success', 'progress_data': {'sql_done': True}},
        ]
        with patch('src.apps.data_factory.services.cleanup.cleanup_schedule.TaskCenterQuerySelector.executor_tasks') as tasks, \
                patch('src.apps.task_center.services.execution.cooperative_executor.wait_until') as wait, \
                patch.object(Schedule, 'verify_complete') as verify:
            tasks.return_value.filter.return_value.values.return_value.first.side_effect = rows
            wait.side_effect = lambda ready, timeout: self.assertTrue(ready())
            Schedule.wait(17)
        wait.assert_called_once()
        verify.assert_called_once_with(7, require_full_cleanup=True)

    def test_sql_stage_terminal_failure_is_not_accepted_as_a_barrier_success(self):
        row = {'business_id': 7, 'status': 'failed', 'progress_data': {'sql_done': True},
               'error_message': 'AUTO_OWNERSHIP_REJECTED'}
        with patch('src.apps.data_factory.services.cleanup.cleanup_schedule.TaskCenterQuerySelector.executor_tasks') as tasks, \
                patch.object(Schedule, 'require_failure_evidence'), patch.object(Schedule, 'verify_complete') as verify:
            tasks.return_value.filter.return_value.values.return_value.first.return_value = row
            with self.assertRaises(DataFactoryError) as error:
                Schedule.wait(17, sql_only=True)
        self.assertIn('AUTO_OWNERSHIP_REJECTED', error.exception.msg)
        verify.assert_not_called()
