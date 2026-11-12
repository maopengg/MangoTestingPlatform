import asyncio
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from django.db import OperationalError
from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from mangotools.contracts import SocketCommandContract, SocketEnvelopeContract
from rest_framework.test import APIRequestFactory, force_authenticate

from src.apps.system.enums import ClientTypeEnum
from src.apps.system.enums import (
    ExecutorModeEnum,
    ExecutorTaskTypeEnum,
    SocketConnectionStatusEnum,
    ExecutorTaskStatusEnum,
    SystemConfigManagementLevelEnum,
)
from src.apps.system.enums import ServerToolsCommandEnum, ServerUiCommandEnum
from src.apps.system.exceptions import SystemError
from src.apps.system.services.socket_link.message_service import SocketMessageService
from src.apps.system.services.configuration.system_config import SYSTEM_CONFIG_REGISTRY, SystemConfigService
from src.apps.task_center.api.views.executor_task import ExecutorTaskViews
from src.apps.task_center.models import SocketConnection
from src.apps.task_center.services.execution.executor_task import ExecutorTaskService
from src.apps.user.models import User


class ExecutorTaskNotificationTest(SimpleTestCase):
    @patch.object(SystemConfigService, "get")
    def test_ui_runtime_snapshot_contains_only_non_secret_runtime_values(self, get_config):
        values = {
            "UI_FIXED_LOCATOR_RETRY_SECONDS": 18,
            "UI_SMART_LOCATOR_TIMEOUT_SECONDS": 45,
            "UI_VISUAL_LOCATOR_ENABLED": True,
            "AI_VISION_BASE_URL": "https://vision.example.com/v1",
            "AI_VISION_MODEL": "vision-model",
        }
        get_config.side_effect = lambda key, default=None: values.get(key, default)

        snapshot = SocketMessageService._ui_runtime_config_snapshot()

        self.assertEqual(snapshot["fixed_locator_retry_seconds"], 18)
        self.assertEqual(snapshot["smart_locator_timeout_seconds"], 45)
        self.assertTrue(snapshot["visual_locator_enabled"])
        self.assertIsNone(snapshot["visual_model_config_version"])
        self.assertNotIn("api_key", snapshot)
        self.assertNotIn("proxy", snapshot)

    def test_visual_proxy_config_is_secret_and_defaults_to_empty(self):
        definition = next(
            item for item in SYSTEM_CONFIG_REGISTRY if item.key == "AI_VISION_PROXY_URL"
        )

        self.assertTrue(definition.is_secret)
        self.assertEqual(
            definition.management_level,
            SystemConfigManagementLevelEnum.STANDARD.value,
        )
        self.assertIsNone(definition.default_value)

    def test_visual_configs_are_exposed_in_system_settings(self):
        visual_keys = {
            'UI_VISUAL_LOCATOR_ENABLED',
            'AI_VISION_USE_SEPARATE_CONFIG',
            'AI_VISION_PROVIDER_TYPE',
            'AI_VISION_API_KEY',
            'AI_VISION_BASE_URL',
            'AI_VISION_MODEL',
            'AI_VISION_TIMEOUT',
            'AI_VISION_PROXY_URL',
        }
        definitions = {
            item.key: item for item in SYSTEM_CONFIG_REGISTRY if item.key in visual_keys
        }

        self.assertEqual(set(definitions), visual_keys)
        self.assertTrue(
            all(
                item.management_level >= SystemConfigManagementLevelEnum.CAUTION.value
                for item in definitions.values()
            )
        )

    @patch.object(SocketMessageService, "_push_task_available")
    @patch.object(ExecutorTaskService, "create")
    @patch.object(SocketMessageService, "_ui_runtime_config_snapshot", return_value={})
    def test_explicit_task_creator_is_not_inferred_from_optional_payload(
            self,
            _runtime_config,
            create_task,
            push_task_available,
    ):
        task = SimpleNamespace(id=18)
        create_task.return_value = task
        command = SocketEnvelopeContract(
            code=200,
            msg="调试步骤",
            user="executor-user",
            is_notice=ClientTypeEnum.ACTUATOR.value,
            data=SocketCommandContract(
                func_name=ServerUiCommandEnum.PAGE_STEPS.value,
                func_args={"id": 8},
            ),
        )

        result = SocketMessageService.send_socket_data(command, created_by=7)

        self.assertIs(result, task)
        self.assertEqual(create_task.call_args.kwargs["created_by"], 7)
        self.assertEqual(create_task.call_args.kwargs["executor_user"], "executor-user")
        push_task_available.assert_called_once_with(task)

    @patch.object(ExecutorTaskService, "serialize")
    @patch.object(ExecutorTaskService, "get_for_user")
    def test_task_detail_view_does_not_use_reserved_viewset_detail_attribute(
            self,
            get_for_user,
            serialize,
    ):
        get_for_user.return_value = SimpleNamespace(id=16)
        serialize.return_value = {"task_id": 16}
        request = APIRequestFactory().get('/api/system/executor/task', {'task_id': 16})
        force_authenticate(request, user=User(id=7, username='task-detail-user'))

        response = ExecutorTaskViews.as_view({'get': 'get_detail'})(request)
        response.render()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['data']['task_id'], 16)
        get_for_user.assert_called_once_with(16, 7)

    def test_realtime_recovery_stays_frequent_and_history_cleanup_runs_overnight(self):
        from pathlib import Path

        project_root = Path(__file__).resolve().parents[3]
        runner_source = (
                project_root / "processes/scheduler/runner.py"
        ).read_text(encoding="utf-8")
        job_source = (
                project_root / "apps/task_center/services/scheduling/system_job.py"
        ).read_text(encoding="utf-8")
        self.assertIn("'recover_executor_tasks',", runner_source)
        self.assertIn('SchedulerSystemJobService.recover_executor_tasks', runner_source)
        self.assertIn("('cleanup_realtime_data', '*/5 * * * *'", runner_source)
        self.assertIn(
            "('clean_executor_task_history', '*/10 2-7 * * *'",
            runner_source,
        )
        self.assertIn("key='recover_executor_tasks'", job_source)
        self.assertIn("key='cleanup_realtime_data'", job_source)
        self.assertIn("key='clean_executor_task_history'", job_source)
        self.assertIn("cron='*/10 2-7 * * *'", job_source)

    def test_element_task_business_id_uses_nested_element_not_page_id(self):
        payload = {
            "id": 12,
            "element_list": [{"id": 87, "name": "提交"}],
        }
        self.assertEqual(
            SocketMessageService._business_id("u_element_check", payload),
            87,
        )

    def test_datetime_text_supports_project_naive_datetime(self):
        self.assertEqual(
            ExecutorTaskService._datetime_text(datetime(2026, 8, 13, 22, 30, 15)),
            '2026-08-13 22:30:15',
        )

    @patch("src.apps.system.services.socket_link.message_service.get_channel_layer")
    def test_task_available_is_only_a_transient_notification(self, get_channel_layer):
        channel_layer = get_channel_layer.return_value
        channel_layer.group_send = AsyncMock()
        notice = SocketEnvelopeContract(
            code=200,
            msg="有新任务",
            is_notice=ClientTypeEnum.ACTUATOR.value,
            data=SocketCommandContract(
                func_name=ServerToolsCommandEnum.TASK_AVAILABLE.value,
                func_args={"task_id": 12},
            ),
        )

        with patch.object(ExecutorTaskService, "create") as create_task:
            result = SocketMessageService.send_socket_data(notice)

        self.assertIsNone(result)
        create_task.assert_not_called()
        channel_layer.group_send.assert_awaited_once()
        group_name, event = channel_layer.group_send.await_args.args
        self.assertEqual(group_name, f"mango.realtime.client.{ClientTypeEnum.ACTUATOR.value}")
        self.assertEqual(event["type"], "socket.notification")
        self.assertEqual(event["payload"]["data"]["func_name"], ServerToolsCommandEnum.TASK_AVAILABLE.value)

    @patch("src.apps.auto_ui.services.elements.ai.element_ai_service.ElementAiService.save_check_result")
    def test_element_task_result_projects_runtime_snapshot_in_terminal_transaction(self, save_result):
        task = type("Task", (), {
            "task_type": ExecutorTaskTypeEnum.ELEMENT_DEEP_CHECK.value,
        })()
        result = {"element_id": 9, "check_mode": "deep", "status": 1}

        ExecutorTaskService._project_business_result(task, result)

        save_result.assert_called_once_with(result)

    @patch("src.apps.auto_ui.services.authentication.ui_auth.UiAuthManager.save_auto_auth_cache")
    def test_auth_capture_task_result_projects_auth_cache(self, save_cache):
        task = type("Task", (), {
            "task_type": ExecutorTaskTypeEnum.AUTH_CAPTURE.value,
        })()
        cache = {"cookies": [], "local_storage": []}

        ExecutorTaskService._project_business_result(
            task,
            {"config_id": 3, "cache_data": cache},
        )

        save_cache.assert_called_once_with(3, cache)

    @patch("src.apps.system.services.socket_link.consumer.ui.UIConsumer.save_page_steps_result")
    def test_page_step_task_result_projects_execution_result(self, save_page_step):
        task = type("Task", (), {
            "task_type": ExecutorTaskTypeEnum.PAGE_STEP_DEBUG.value,
        })()
        result = {"id": 8, "status": 1, "is_final": True}

        ExecutorTaskService._project_business_result(task, result)

        save_page_step.assert_called_once_with(result)

    @patch("src.apps.system.services.socket_link.consumer.ui.UIConsumer.save_test_case_result")
    def test_case_task_result_projects_execution_result(self, save_case):
        task = type("Task", (), {
            "task_type": ExecutorTaskTypeEnum.UI_CASE.value,
        })()
        result = {"id": 5, "status": 0, "is_final": True}

        ExecutorTaskService._project_business_result(task, result)

        save_case.assert_called_once_with(result)

    @patch(
        "src.apps.system.services.socket_link.consumer.system."
        "SystemConsumer.save_actuator_config_snapshot"
    )
    def test_config_command_result_projects_snapshot_for_polling_api(self, save_snapshot):
        request_id = 'config-request-1'
        task = SimpleNamespace(
            task_type=ExecutorTaskTypeEnum.CONFIG_COMMAND.value,
            payload={
                'func_name': ServerToolsCommandEnum.GET_ACTUATOR_CONFIG.value,
                'func_args': {'request_id': request_id},
            },
            executor_user=SimpleNamespace(username='executor-user'),
        )

        ExecutorTaskService._project_business_result(task, {
            'status': True,
            'config': {'runtime': {'is_open': True}},
        })

        save_snapshot.assert_called_once_with({
            'request_id': request_id,
            'status': True,
            'username': 'executor-user',
            'config': {'runtime': {'is_open': True}},
        })

    @patch(
        "src.apps.system.services.socket_link.consumer.system."
        "SystemConsumer.save_actuator_config_save_result"
    )
    def test_config_command_result_projects_save_failure_for_polling_api(self, save_result):
        request_id = 'config-request-2'
        task = SimpleNamespace(
            task_type=ExecutorTaskTypeEnum.CONFIG_COMMAND.value,
            payload={
                'func_name': ServerToolsCommandEnum.UPDATE_ACTUATOR_CONFIG.value,
                'func_args': {'request_id': request_id},
            },
            executor_user=SimpleNamespace(username='executor-user'),
        )

        ExecutorTaskService._project_business_result(task, {
            'status': False,
            'message': '执行器配置保存失败：无效配置',
            'config': {'runtime': {}},
        })

        save_result.assert_called_once_with({
            'request_id': request_id,
            'status': False,
            'username': 'executor-user',
            'message': '执行器配置保存失败：无效配置',
            'config': {'runtime': {}},
        })


class RealtimeCompletionDispatcherTest(SimpleTestCase):
    def test_dispatcher_sends_ui_case_result_through_local_web_connection(self):
        from src.processes.realtime.completion_dispatcher import (
            ExecutorTaskCompletionDispatcher,
        )

        consumer = SimpleNamespace(send_json=AsyncMock())
        registry = SimpleNamespace(
            get_web_connections=AsyncMock(
                return_value=[SimpleNamespace(consumer=consumer)]
            )
        )
        dispatcher = ExecutorTaskCompletionDispatcher(registry)
        finished_at = timezone.now()
        task = SimpleNamespace(
            id=18,
            task_type=ExecutorTaskTypeEnum.UI_CASE.value,
            status=ExecutorTaskStatusEnum.SUCCESS.value,
            created_by_id=7,
            created_by=SimpleNamespace(username='task-owner'),
            result_data={'name': '创建订单', 'status': 1},
            payload={'func_args': {'name': '创建订单'}},
            business_type='u_case',
            business_id=4,
            error_message=None,
            started_at=finished_at - timedelta(seconds=8),
            finished_at=finished_at,
        )

        asyncio.run(dispatcher._deliver(task))

        registry.get_web_connections.assert_awaited_once_with(7)
        payload = consumer.send_json.await_args.args[0]
        self.assertEqual(payload['data']['func_name'], 'executor_task_result')
        self.assertEqual(payload['data']['func_args']['task_id'], 18)
        self.assertEqual(payload['user'], 'task-owner')
        self.assertIn('创建订单', payload['msg'])
        self.assertIn('执行通过', payload['msg'])


class ExecutorTaskServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            name='统一任务用户',
            username='executor-task-user',
            password='password',
        )

    def create_connection(self, *, is_open=False, stale=False):
        return SocketConnection.objects.create(
            user=self.user,
            client_type=ClientTypeEnum.ACTUATOR.value,
            channel_name='local.executor-task',
            service_instance='test-realtime',
            status=SocketConnectionStatusEnum.ONLINE.value,
            is_open=is_open,
            last_seen_at=timezone.now() - timedelta(seconds=120) if stale else timezone.now(),
        )

    def create_task(self, **kwargs):
        values = {
            'task_type': ExecutorTaskTypeEnum.ELEMENT_DEEP_CHECK.value,
            'created_by': self.user,
            'executor_mode': ExecutorModeEnum.SELF.value,
            'executor_user': self.user,
            'payload': {'func_name': 'u_element_check', 'func_args': {'check_id': 'check-1'}},
            'business_type': 'ui_element_check',
            'business_id': 1,
        }
        values.update(kwargs)
        return ExecutorTaskService.create(**values)

    def test_online_executor_creates_pending_task_and_uses_table_id_as_task_id(self):
        self.create_connection()
        task = self.create_task()
        self.assertIsInstance(task.id, int)
        self.assertEqual(task.status, ExecutorTaskStatusEnum.PENDING.value)

    def test_offline_executor_task_waits_until_schedule_deadline(self):
        task = self.create_task()
        self.assertEqual(task.status, ExecutorTaskStatusEnum.WAITING_EXECUTOR.value)
        self.assertIsNotNone(task.schedule_deadline)

    def test_offline_interactive_task_can_fail_fast_with_auditable_task_id(self):
        task = self.create_task(schedule_timeout_seconds=0)
        self.assertIsInstance(task.id, int)
        self.assertEqual(task.status, ExecutorTaskStatusEnum.FAILED.value)
        self.assertEqual(task.error_code, "SELF_EXECUTOR_OFFLINE")
        self.assertIsNone(task.schedule_deadline)

    def test_cleanup_history_uses_one_retention_period_for_all_finished_tasks(self):
        success_task = self.create_task()
        failed_task = self.create_task()
        active_task = self.create_task()
        recent_task = self.create_task()
        old_finished_at = timezone.now() - timedelta(days=8)
        recent_finished_at = timezone.now() - timedelta(days=1)
        task_model = type(success_task)
        task_model.objects.filter(id=success_task.id).update(
            status=ExecutorTaskStatusEnum.SUCCESS.value,
            finished_at=old_finished_at,
        )
        task_model.objects.filter(id=failed_task.id).update(
            status=ExecutorTaskStatusEnum.FAILED.value,
            finished_at=old_finished_at,
        )
        task_model.objects.filter(id=recent_task.id).update(
            status=ExecutorTaskStatusEnum.CANCELLED.value,
            finished_at=recent_finished_at,
        )

        deleted = ExecutorTaskService.cleanup_history(retention_days=7)

        self.assertEqual(deleted, 2)
        self.assertFalse(task_model.objects.filter(id=success_task.id).exists())
        self.assertFalse(task_model.objects.filter(id=failed_task.id).exists())
        self.assertTrue(task_model.objects.filter(id=active_task.id).exists())
        self.assertTrue(task_model.objects.filter(id=recent_task.id).exists())

    def test_claim_running_heartbeat_and_result_form_single_state_machine(self):
        connection = self.create_connection()
        task = self.create_task()
        claimed = ExecutorTaskService.claim(
            connection_id=str(connection.connection_id),
            username=self.user.username,
        )
        self.assertEqual([item.id for item in claimed], [task.id])
        running = ExecutorTaskService.mark_running(task.id, str(connection.connection_id), self.user.username)
        self.assertEqual(running.status, ExecutorTaskStatusEnum.RUNNING.value)
        heartbeat = ExecutorTaskService.heartbeat(task.id, str(connection.connection_id), self.user.username)
        self.assertGreater(heartbeat.lease_expires_at, timezone.now())
        completed = ExecutorTaskService.complete(
            task_id=task.id,
            connection_id=str(connection.connection_id),
            username=self.user.username,
            success=True,
            result_data={'check_id': 'check-1', 'status': 1},
        )
        self.assertEqual(completed.status, ExecutorTaskStatusEnum.SUCCESS.value)
        self.assertEqual(completed.result_data['check_id'], 'check-1')

    def test_claim_retries_mysql_deadlock_with_backoff(self):
        deadlock = OperationalError(1213, 'Deadlock found when trying to get lock')
        with (
            patch.object(ExecutorTaskService, '_claim_once', side_effect=[deadlock, []]) as claim_once,
            patch('src.apps.task_center.services.execution.executor_task.random.uniform', return_value=0),
            patch('src.apps.task_center.services.execution.executor_task.time.sleep') as sleep,
        ):
            claimed = ExecutorTaskService.claim(
                connection_id='connection-id',
                username=self.user.username,
            )

        self.assertEqual(claimed, [])
        self.assertEqual(claim_once.call_count, 2)
        sleep.assert_called_once_with(ExecutorTaskService.DEADLOCK_BASE_DELAY_SECONDS)

    def test_claim_does_not_retry_non_deadlock_database_error(self):
        database_error = OperationalError(1205, 'Lock wait timeout exceeded')
        with (
            patch.object(ExecutorTaskService, '_claim_once', side_effect=database_error) as claim_once,
            patch('src.apps.task_center.services.execution.executor_task.time.sleep') as sleep,
            self.assertRaises(OperationalError),
        ):
            ExecutorTaskService.claim(
                connection_id='connection-id',
                username=self.user.username,
            )

        claim_once.assert_called_once()
        sleep.assert_not_called()

    @patch.object(ExecutorTaskService, 'recover_expired')
    def test_claim_does_not_run_global_recovery(self, recover_expired):
        connection = self.create_connection()
        task = self.create_task()

        claimed = ExecutorTaskService.claim(
            connection_id=str(connection.connection_id),
            username=self.user.username,
        )

        self.assertEqual([item.id for item in claimed], [task.id])
        recover_expired.assert_not_called()

    @patch.object(SocketMessageService, "_push_notification")
    def test_ui_case_completion_notification_contains_readable_result(self, push_notification):
        started_at = timezone.now() - timedelta(seconds=80)
        task = self.create_task(
            task_type=ExecutorTaskTypeEnum.UI_CASE.value,
            business_type='u_case',
            business_id=4,
            payload={
                'func_name': 'u_case',
                'func_args': {'id': 4, 'name': '检查智能起草是否可用'},
            },
        )
        type(task).objects.filter(id=task.id).update(
            status=ExecutorTaskStatusEnum.SUCCESS.value,
            result_data={'id': 4, 'name': '检查智能起草是否可用', 'status': 1},
            started_at=started_at,
            finished_at=timezone.now(),
        )

        SocketMessageService.send_executor_task_result(task.id)

        notice, client_type = push_notification.call_args.args
        self.assertEqual(client_type, ClientTypeEnum.WEB.value)
        self.assertEqual(notice.code, 200)
        self.assertIn('检查智能起草是否可用', notice.msg)
        self.assertIn('执行通过', notice.msg)
        self.assertIn('1分20秒', notice.msg)
        self.assertEqual(notice.data.func_name, 'executor_task_result')
        self.assertEqual(notice.data.func_args['business_id'], 4)
        self.assertEqual(notice.data.func_args['status_text'], '执行通过')

    @patch.object(SocketMessageService, "_push_notification")
    def test_failed_ui_case_completion_notification_explains_reason(self, push_notification):
        task = self.create_task(
            task_type=ExecutorTaskTypeEnum.UI_CASE.value,
            business_type='u_case',
            business_id=4,
            payload={
                'func_name': 'u_case',
                'func_args': {'id': 4, 'name': '检查智能起草是否可用'},
            },
        )
        type(task).objects.filter(id=task.id).update(
            status=ExecutorTaskStatusEnum.FAILED.value,
            result_data={'id': 4, 'name': '检查智能起草是否可用', 'status': 0},
            error_message='未找到“智能起草”按钮',
            finished_at=timezone.now(),
        )

        SocketMessageService.send_executor_task_result(task.id)

        notice = push_notification.call_args.args[0]
        self.assertEqual(notice.code, 300)
        self.assertIn('执行失败', notice.msg)
        self.assertIn('失败原因：未找到“智能起草”按钮', notice.msg)
        self.assertEqual(notice.data.func_args['error_message'], '未找到“智能起草”按钮')

    def test_finishing_ui_task_is_discoverable_by_realtime_dispatcher(self):
        from src.processes.realtime.completion_dispatcher import (
            ExecutorTaskCompletionDispatcher,
        )

        task = self.create_task(task_type=ExecutorTaskTypeEnum.UI_CASE.value)

        ExecutorTaskService._finish(
            task,
            ExecutorTaskStatusEnum.FAILED.value,
            'business_failed',
            '测试失败',
        )

        loaded = ExecutorTaskCompletionDispatcher._load_batch(
            task.finished_at - timedelta(seconds=1),
            0,
            10,
        )
        self.assertIn(task.id, [item.id for item in loaded])

    def test_claim_respects_current_task_type_capacity(self):
        connection = self.create_connection()
        first = self.create_task(task_type=ExecutorTaskTypeEnum.PERF_EXECUTION.value)
        self.create_task(task_type=ExecutorTaskTypeEnum.PERF_EXECUTION.value, business_id=2)

        claimed = ExecutorTaskService.claim(
            connection_id=str(connection.connection_id),
            username=self.user.username,
            capacity=5,
            supported_task_types=[ExecutorTaskTypeEnum.PERF_EXECUTION.value],
            protocol_versions={ExecutorTaskTypeEnum.PERF_EXECUTION.value: 1},
            capability_capacities={"perf": 1},
            task_type_capacities={ExecutorTaskTypeEnum.PERF_EXECUTION.value: 1},
        )

        self.assertEqual([item.id for item in claimed], [first.id])

    def test_expired_unstarted_claim_is_released_without_consuming_retry(self):
        connection = self.create_connection()
        task = self.create_task()
        ExecutorTaskService.claim(connection_id=str(connection.connection_id), username=self.user.username)
        task.refresh_from_db()
        task.lease_expires_at = timezone.now() - timedelta(seconds=1)
        task.save(update_fields=['lease_expires_at'])
        recovered = ExecutorTaskService.recover_expired()
        task.refresh_from_db()
        self.assertEqual(recovered['retried'], 1)
        self.assertEqual(task.status, ExecutorTaskStatusEnum.WAITING_EXECUTOR.value)
        self.assertEqual(task.retry_count, 0)
        self.assertIsNone(task.executor_connection_id)

    def test_expired_running_read_only_task_consumes_retry(self):
        connection = self.create_connection()
        task = self.create_task()
        ExecutorTaskService.claim(connection_id=str(connection.connection_id), username=self.user.username)
        ExecutorTaskService.mark_running(task.id, str(connection.connection_id), self.user.username)
        task.refresh_from_db()
        task.lease_expires_at = timezone.now() - timedelta(seconds=1)
        task.save(update_fields=['lease_expires_at'])

        recovered = ExecutorTaskService.recover_expired()

        task.refresh_from_db()
        self.assertEqual(recovered['retried'], 1)
        self.assertEqual(task.status, ExecutorTaskStatusEnum.PENDING.value)
        self.assertEqual(task.retry_count, 1)

    def test_public_task_retry_releases_previous_executor_user(self):
        connection = self.create_connection(is_open=True)
        task = ExecutorTaskService.create(
            task_type=ExecutorTaskTypeEnum.ELEMENT_DEEP_CHECK.value,
            created_by=self.user,
            executor_mode=ExecutorModeEnum.PUBLIC.value,
            payload={'func_name': 'u_element_check', 'func_args': {'check_id': 'public-check'}},
            business_type='ui_element_check',
        )
        ExecutorTaskService.claim(
            connection_id=str(connection.connection_id),
            username=self.user.username,
        )
        task.refresh_from_db()
        self.assertEqual(task.executor_user_id, self.user.id)
        task.lease_expires_at = timezone.now() - timedelta(seconds=1)
        task.save(update_fields=['lease_expires_at'])

        ExecutorTaskService.recover_expired()

        task.refresh_from_db()
        self.assertEqual(task.status, ExecutorTaskStatusEnum.PENDING.value)
        self.assertIsNone(task.executor_user_id)

    def test_duplicate_result_submission_returns_existing_terminal_task(self):
        connection = self.create_connection()
        task = self.create_task()
        ExecutorTaskService.claim(connection_id=str(connection.connection_id), username=self.user.username)
        ExecutorTaskService.mark_running(task.id, str(connection.connection_id), self.user.username)
        first = ExecutorTaskService.complete(
            task_id=task.id,
            connection_id=str(connection.connection_id),
            username=self.user.username,
            success=True,
            result_data={'status': 1},
        )
        second = ExecutorTaskService.complete(
            task_id=task.id,
            connection_id=str(connection.connection_id),
            username=self.user.username,
            success=True,
            result_data={'status': 1},
        )
        self.assertEqual(first.id, second.id)
        self.assertEqual(second.status, ExecutorTaskStatusEnum.SUCCESS.value)

    def test_different_terminal_result_cannot_overwrite_completed_task(self):
        connection = self.create_connection()
        task = self.create_task()
        ExecutorTaskService.claim(connection_id=str(connection.connection_id), username=self.user.username)
        ExecutorTaskService.mark_running(task.id, str(connection.connection_id), self.user.username)
        ExecutorTaskService.complete(
            task_id=task.id,
            connection_id=str(connection.connection_id),
            username=self.user.username,
            success=True,
            result_data={'status': 1},
        )

        with self.assertRaises(SystemError):
            ExecutorTaskService.complete(
                task_id=task.id,
                connection_id=str(connection.connection_id),
                username=self.user.username,
                success=False,
                result_data={'status': 0},
                error_code='late_failure',
            )

    def test_reconnected_executor_can_replay_current_attempt_result(self):
        old_connection = self.create_connection()
        task = self.create_task()
        ExecutorTaskService.claim(
            connection_id=str(old_connection.connection_id),
            username=self.user.username,
        )
        ExecutorTaskService.mark_running(
            task.id,
            str(old_connection.connection_id),
            self.user.username,
        )
        old_connection.status = SocketConnectionStatusEnum.OFFLINE.value
        old_connection.save(update_fields=['status'])
        self.create_connection()

        completed = ExecutorTaskService.complete(
            task_id=task.id,
            connection_id=str(old_connection.connection_id),
            username=self.user.username,
            attempt=0,
            success=True,
            result_data={'status': 1},
        )

        self.assertEqual(completed.status, ExecutorTaskStatusEnum.SUCCESS.value)

    def test_old_attempt_result_cannot_overwrite_retried_task(self):
        connection = self.create_connection()
        task = self.create_task()
        ExecutorTaskService.claim(
            connection_id=str(connection.connection_id),
            username=self.user.username,
        )
        task.refresh_from_db()
        task.retry_count = 1
        task.status = ExecutorTaskStatusEnum.RUNNING.value
        task.save(update_fields=['retry_count', 'status'])

        with self.assertRaises(SystemError):
            ExecutorTaskService.complete(
                task_id=task.id,
                connection_id=str(connection.connection_id),
                username=self.user.username,
                attempt=0,
                success=True,
                result_data={'status': 1},
            )

    @patch('src.apps.task_center.services.execution.executor_task.ExecutorTaskService._project_business_result')
    def test_projection_failure_is_terminal_and_pollable(self, project_result):
        project_result.side_effect = RuntimeError('projection failed')
        connection = self.create_connection()
        task = self.create_task()
        ExecutorTaskService.claim(connection_id=str(connection.connection_id), username=self.user.username)
        ExecutorTaskService.mark_running(task.id, str(connection.connection_id), self.user.username)

        completed = ExecutorTaskService.complete(
            task_id=task.id,
            connection_id=str(connection.connection_id),
            username=self.user.username,
            success=True,
            result_data={'status': 1},
        )

        self.assertEqual(completed.status, ExecutorTaskStatusEnum.FAILED.value)
        self.assertEqual(completed.error_code, 'result_projection_failed')

    def test_schedule_timeout_becomes_terminal_and_pollable(self):
        task = self.create_task()
        task.schedule_deadline = timezone.now() - timedelta(seconds=1)
        task.save(update_fields=['schedule_deadline'])
        ExecutorTaskService.recover_expired()
        task.refresh_from_db()
        self.assertEqual(task.status, ExecutorTaskStatusEnum.TIMEOUT.value)
        self.assertEqual(task.error_code, 'schedule_timeout')

    def test_recover_expired_limits_each_state_transition_to_batch_size(self):
        tasks = [self.create_task(business_id=index) for index in range(1, 4)]
        type(tasks[0]).objects.filter(id__in=[task.id for task in tasks]).update(
            schedule_deadline=timezone.now() - timedelta(seconds=1),
        )

        first = ExecutorTaskService.recover_expired(batch_size=2)
        remaining = type(tasks[0]).objects.filter(
            id__in=[task.id for task in tasks],
            status=ExecutorTaskStatusEnum.WAITING_EXECUTOR.value,
        ).count()
        second = ExecutorTaskService.recover_expired(batch_size=2)

        self.assertEqual(first['waiting_timeout'], 2)
        self.assertEqual(remaining, 1)
        self.assertEqual(second['waiting_timeout'], 1)

    def test_cancel_requested_task_is_not_requeued_after_executor_disconnects(self):
        connection = self.create_connection()
        task = self.create_task()
        ExecutorTaskService.claim(
            connection_id=str(connection.connection_id),
            username=self.user.username,
        )
        task.refresh_from_db()
        task.cancel_requested_at = timezone.now()
        task.lease_expires_at = timezone.now() - timedelta(seconds=1)
        task.save(update_fields=['cancel_requested_at', 'lease_expires_at'])

        recovered = ExecutorTaskService.recover_expired()

        task.refresh_from_db()
        self.assertEqual(recovered['cancelled'], 1)
        self.assertEqual(task.status, ExecutorTaskStatusEnum.CANCELLED.value)

    def test_unclaimed_pending_task_also_obeys_schedule_deadline(self):
        self.create_connection()
        task = self.create_task()
        self.assertEqual(task.status, ExecutorTaskStatusEnum.PENDING.value)
        task.schedule_deadline = timezone.now() - timedelta(seconds=1)
        task.save(update_fields=['schedule_deadline'])

        ExecutorTaskService.recover_expired()

        task.refresh_from_db()
        self.assertEqual(task.status, ExecutorTaskStatusEnum.TIMEOUT.value)
        self.assertEqual(task.error_code, 'schedule_timeout')

    def test_public_task_can_only_be_claimed_by_open_executor(self):
        connection = self.create_connection(is_open=False)
        task = ExecutorTaskService.create(
            task_type=ExecutorTaskTypeEnum.PAGE_SCAN.value,
            created_by=self.user,
            executor_mode=ExecutorModeEnum.PUBLIC.value,
            payload={'func_name': 'u_page_scan', 'func_args': {}},
            business_type='page_scan',
        )
        claimed = ExecutorTaskService.claim(
            connection_id=str(connection.connection_id),
            username=self.user.username,
        )
        self.assertNotIn(task.id, [item.id for item in claimed])

    def test_idempotency_key_returns_existing_task(self):
        self.create_connection()
        first = self.create_task(message_key='element-check:1')
        second = self.create_task(message_key='element-check:1')
        self.assertEqual(first.id, second.id)

    def test_custom_execution_timeout_is_preserved_when_running_starts(self):
        connection = self.create_connection()
        task = self.create_task(
            schedule_timeout_seconds=20,
            execution_timeout_seconds=900,
        )
        ExecutorTaskService.claim(
            connection_id=str(connection.connection_id),
            username=self.user.username,
        )

        running = ExecutorTaskService.mark_running(
            task.id,
            str(connection.connection_id),
            self.user.username,
        )

        remaining = (running.expired_at - timezone.now()).total_seconds()
        self.assertGreaterEqual(remaining, 895)
        self.assertLessEqual(remaining, 900)

    def test_claim_filters_unsupported_protocol_version(self):
        connection = self.create_connection()
        task = self.create_task(payload={
            'schema_version': 2,
            'func_name': 'u_element_check',
            'func_args': {'check_id': 'check-v2'},
        })

        claimed = ExecutorTaskService.claim(
            connection_id=str(connection.connection_id),
            username=self.user.username,
            protocol_versions={'*': 1},
        )

        self.assertNotIn(task.id, [item.id for item in claimed])

    def test_draining_connection_releases_unstarted_claim_and_stops_claiming(self):
        connection = self.create_connection()
        task = self.create_task()
        ExecutorTaskService.claim(
            connection_id=str(connection.connection_id),
            username=self.user.username,
        )

        ExecutorTaskService.set_connection_draining(
            connection_id=str(connection.connection_id),
            username=self.user.username,
            draining=True,
        )

        task.refresh_from_db()
        self.assertEqual(task.status, ExecutorTaskStatusEnum.WAITING_EXECUTOR.value)
        self.assertEqual(
            ExecutorTaskService.claim(
                connection_id=str(connection.connection_id),
                username=self.user.username,
            ),
            [],
        )
