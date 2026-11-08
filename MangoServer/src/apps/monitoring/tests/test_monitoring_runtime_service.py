from types import SimpleNamespace
from unittest import TestCase, mock
import io
import tempfile
from pathlib import Path

from django.test import override_settings

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
    def test_start_persists_missing_log_path_before_process_and_keeps_existing_path(self):
        for original in (None, '', '  ', 'monitoring/logs/existing.log'):
            with self.subTest(log_path=original), tempfile.TemporaryDirectory() as directory:
                persisted = {'log_path': original}
                task = SimpleNamespace(id=9, name='示例脚本', status=MonitoringTaskStatusEnum.STARTING.value,
                                       pid=None, script_content='print("ok")', log_path=original,
                                       refresh_from_db=mock.Mock())

                def save(*, update_fields):
                    if 'log_path' in update_fields:
                        persisted['log_path'] = task.log_path
                task.save = mock.Mock(side_effect=save)
                process = mock.Mock(pid=123, stdout=io.StringIO(''))
                process.poll.return_value = None

                def spawn(*args, **kwargs):
                    self.assertEqual(persisted['log_path'], task.log_path)
                    self.assertTrue(Path(MonitoringTaskRunner._get_absolute_path(task.log_path)).is_file())
                    return process

                worker = MonitoringTaskRunner()
                with override_settings(BASE_DIR=directory, MONITORING_SCRIPT_DIR=directory + '/scripts',
                                       MONITORING_LOG_DIR=directory + '/logs'), \
                        mock.patch('src.apps.monitoring.services.runner.subprocess.Popen', side_effect=spawn), \
                        mock.patch('src.apps.monitoring.services.runner.threading.Thread'):
                    worker.start_task(task)
                    self.assertEqual(task.status, MonitoringTaskStatusEnum.RUNNING.value)
                    self.assertEqual(task.pid, 123)
                    self.assertIsNotNone(task.started_at)
                    if original and original.strip():
                        self.assertEqual(task.log_path, original)
                    else:
                        self.assertRegex(task.log_path, r'^monitoring/logs/[0-9a-f]{32}\.log$')
                    chosen_path = task.log_path
                    worker.running_processes.clear()
                    task.status = MonitoringTaskStatusEnum.STARTING.value
                    task.pid = None
                    worker.start_task(task)
                    self.assertEqual(task.log_path, chosen_path)
                    content = Path(worker._get_absolute_path(task.log_path)).read_text()
                    self.assertEqual(content.count('开始新的执行'), 2)
                writes = [call for call in task.save.call_args_list if call.kwargs['update_fields'] == ['log_path']]
                self.assertEqual(len(writes), 0 if original and original.strip() else 1)

    def test_log_timestamps_support_both_timezone_modes(self):
        for enabled in (False, True):
            with self.subTest(use_tz=enabled), override_settings(USE_TZ=enabled):
                self.assertRegex(MonitoringTaskRunner._log_timestamp(), r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$')
                with mock.patch.object(MonitoringTaskRunner, '_append_log') as write:
                    MonitoringTaskRunner().append_task_log(SimpleNamespace(log_path='monitoring/logs/example.log'), '示例原因')
                self.assertIn('示例原因', write.call_args.args[1])
    def test_script_failure_keeps_output_when_file_logging_is_unwritable(self):
        task = SimpleNamespace(id=9, name='示例脚本', status=MonitoringTaskStatusEnum.STARTING.value,
                               pid=None, script_content='pass', log_path='monitoring/logs/example.log',
                               save=mock.Mock(), refresh_from_db=mock.Mock())
        process = mock.Mock(pid=123, stdout=io.StringIO("ModuleNotFoundError: No module named 'example_missing_package'\n"))
        process.wait.return_value = 1
        worker = MonitoringTaskRunner()

        def thread(target, **kwargs):
            result = mock.Mock()
            result.start.side_effect = target
            return result

        with tempfile.TemporaryDirectory() as directory, \
                override_settings(BASE_DIR=directory, MONITORING_SCRIPT_DIR=directory + '/scripts', MONITORING_LOG_DIR=directory + '/logs'), \
                mock.patch('src.apps.monitoring.services.runner.subprocess.Popen', return_value=process), \
                mock.patch('src.apps.monitoring.services.runner.threading.Thread', side_effect=thread), \
                mock.patch.object(worker, '_append_log', side_effect=[None, PermissionError('example')]), \
                mock.patch('src.apps.monitoring.services.task_diagnostic.MonitoringTaskDiagnosticService.record') as diagnostic:
            worker.start_task(task)
        self.assertEqual(task.status, MonitoringTaskStatusEnum.FAILED.value)
        self.assertEqual(task.exit_code, 1)
        diagnostic.assert_called_once()
        self.assertIn('example_missing_package', diagnostic.call_args.args[1])

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

        append_log_mock.side_effect = PermissionError('example log permission')
        with mock.patch('src.processes.monitoring.runner.MonitoringTaskDiagnosticService.record') as diagnostic:
            service.reconcile()
        diagnostic.assert_called_once()
        self.assertIn('RuntimeError', diagnostic.call_args.args[1])
        self.assertEqual(task.status, MonitoringTaskStatusEnum.FAILED.value)
        self.assertEqual(task.exit_code, -1)
        task.save.assert_called_once()
        append_log_mock.assert_called_once()
        report_system_error_mock.assert_called_once()
