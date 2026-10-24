from types import SimpleNamespace
from unittest import TestCase, mock

from src.apps.monitoring.enums import MonitoringTaskStatusEnum
from src.apps.monitoring.services.runner import MonitoringTaskRunner
from src.processes.monitoring.runner import MonitoringRuntimeService


class FakeQuerySet:
    def __init__(self, values):
        self.values = values

    def __iter__(self):
        return iter(self.values)

    def first(self):
        return self.values[0] if self.values else None


class MonitoringRuntimeServiceTest(TestCase):
    def test_stop_task_clears_runtime_fields(self):
        process = mock.Mock()
        process.poll.return_value = 0
        task = SimpleNamespace(
            id=3,
            status=MonitoringTaskStatusEnum.RUNNING.value,
            pid=123,
            exit_code=None,
            stopped_at=None,
            save=mock.Mock(),
        )
        task_runner = MonitoringTaskRunner()
        task_runner.running_processes[task.id] = process

        task_runner.stop_task(task, update_status=True)

        self.assertEqual(task.status, MonitoringTaskStatusEnum.STOPPED.value)
        self.assertIsNone(task.pid)
        self.assertEqual(task.exit_code, 0)
        self.assertIsNotNone(task.stopped_at)

    @mock.patch('src.processes.monitoring.runner.runner.stop_task')
    @mock.patch('src.processes.monitoring.runner.runner.start_task')
    @mock.patch('src.processes.monitoring.runner.runner.active_task_ids', return_value={2})
    @mock.patch('src.processes.monitoring.runner.MonitoringQuerySelector.monitoring_task')
    def test_reconcile_starts_missing_and_stops_undesired_tasks(
            self,
            monitoring_task_mock,
            _active_mock,
            start_mock,
            stop_mock,
    ):
        desired = SimpleNamespace(id=1, status=MonitoringTaskStatusEnum.RUNNING.value)
        undesired = SimpleNamespace(id=2, status=MonitoringTaskStatusEnum.STOPPED.value)

        def filter_side_effect(**kwargs):
            if 'status__in' in kwargs:
                return FakeQuerySet([desired])
            if kwargs.get('id') == 2:
                return FakeQuerySet([undesired])
            return FakeQuerySet([])

        monitoring_task_mock.return_value.filter.side_effect = filter_side_effect
        service = MonitoringRuntimeService(instance_name='monitoring-test', poll_interval=1)

        service.reconcile()

        start_mock.assert_called_once_with(desired)
        stop_mock.assert_called_once_with(undesired, timeout=5.0, update_status=False)

    @mock.patch('src.processes.monitoring.runner.runner.stop_task_by_id')
    @mock.patch('src.processes.monitoring.runner.runner.start_task')
    @mock.patch('src.processes.monitoring.runner.runner.active_task_ids', return_value={9})
    @mock.patch('src.processes.monitoring.runner.MonitoringQuerySelector.monitoring_task')
    def test_reconcile_stops_orphan_process_when_record_was_deleted(
            self,
            monitoring_task_mock,
            _active_mock,
            start_mock,
            stop_by_id_mock,
    ):
        monitoring_task_mock.return_value.filter.return_value = FakeQuerySet([])
        service = MonitoringRuntimeService(instance_name='monitoring-test', poll_interval=1)

        service.reconcile()

        start_mock.assert_not_called()
        stop_by_id_mock.assert_called_once_with(9, timeout=5.0)

    @mock.patch('src.common.decorators.system_error.report_system_error')
    @mock.patch('src.processes.monitoring.runner.runner.append_task_log')
    @mock.patch('src.processes.monitoring.runner.runner.start_task', side_effect=RuntimeError('boom'))
    @mock.patch('src.processes.monitoring.runner.runner.active_task_ids', return_value=set())
    @mock.patch('src.processes.monitoring.runner.MonitoringQuerySelector.monitoring_task')
    def test_reconcile_marks_start_failure(
            self,
            monitoring_task_mock,
            _active_mock,
            _start_mock,
            append_log_mock,
            report_system_error_mock,
    ):
        task = SimpleNamespace(
            id=7,
            status=MonitoringTaskStatusEnum.STARTING.value,
            pid=None,
            exit_code=None,
            stopped_at=None,
            save=mock.Mock(),
        )
        monitoring_task_mock.return_value.filter.return_value = FakeQuerySet([task])
        service = MonitoringRuntimeService(instance_name='monitoring-test', poll_interval=1)

        service.reconcile()

        self.assertEqual(task.status, MonitoringTaskStatusEnum.FAILED.value)
        self.assertEqual(task.exit_code, -1)
        task.save.assert_called_once()
        append_log_mock.assert_called_once()
        report_system_error_mock.assert_called_once()
