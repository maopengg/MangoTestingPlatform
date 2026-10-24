from contextlib import nullcontext
from types import SimpleNamespace
from unittest import TestCase, mock

from src.apps.monitoring.enums import MonitoringTaskStatusEnum
from src.apps.monitoring.exceptions import MonitoringError
from src.apps.monitoring.services.task_control import MonitoringTaskControlService


class MonitoringTaskControlServiceTest(TestCase):
    @mock.patch(
        'src.apps.monitoring.services.task_control.ServiceHeartbeatService.count_online_instances',
        return_value=0,
    )
    def test_request_start_rejects_when_runtime_service_is_offline(self, _heartbeat_mock):
        task = SimpleNamespace(id=1)

        with self.assertRaises(MonitoringError):
            MonitoringTaskControlService.request_start(task)

    @mock.patch('src.apps.monitoring.services.task_control.transaction.atomic', return_value=nullcontext())
    @mock.patch('src.apps.monitoring.services.task_control.MonitoringTask.objects.select_for_update')
    @mock.patch(
        'src.apps.monitoring.services.task_control.ServiceHeartbeatService.count_online_instances',
        return_value=1,
    )
    def test_request_start_sets_starting_until_process_is_created(
            self,
            _heartbeat_mock,
            select_for_update_mock,
            _atomic_mock,
    ):
        locked_task = SimpleNamespace(
            id=1,
            status=MonitoringTaskStatusEnum.STOPPED.value,
            pid=123,
            exit_code=9,
            started_at='old',
            stopped_at='old',
            save=mock.Mock(),
        )
        select_for_update_mock.return_value.get.return_value = locked_task

        result = MonitoringTaskControlService.request_start(SimpleNamespace(id=1))

        self.assertIs(result, locked_task)
        self.assertEqual(locked_task.status, MonitoringTaskStatusEnum.STARTING.value)
        self.assertIsNone(locked_task.pid)
        self.assertIsNone(locked_task.exit_code)
        self.assertIsNone(locked_task.started_at)
        self.assertIsNone(locked_task.stopped_at)
        locked_task.save.assert_called_once()
