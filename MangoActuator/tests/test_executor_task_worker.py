import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from src.services.executor_task_worker import ExecutorTaskWorker
from src.services.runtime_config import get_task_ui_runtime_config
from src.services.ui.case_concurrency import UiCaseConcurrency
from src.network.http.apis.actuator_tasks import ActuatorTaskApi
from src.network.http.apis.base import ApiError
from src.storage.sqlite import ExecutorTaskResultOutbox
from src.tools.executor_task_context import (
    get_executor_task_context,
    get_executor_task_log_context,
    reset_executor_task_id,
    set_executor_task_id,
)
from src.tools.decorator.error_handle import async_error_handle


class ExecutorTaskWorkerTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        ExecutorTaskWorker._running_tasks.clear()
        ExecutorTaskWorker._wake_event.clear()
        UiCaseConcurrency.reset()
        for row in ExecutorTaskResultOutbox.list_due(1000):
            ExecutorTaskResultOutbox.delete(row['id'])

    async def asyncTearDown(self):
        UiCaseConcurrency.reset()

    def test_performance_capability_requires_k6_binary(self):
        from src.services.capabilities import CapabilityRegistry

        with patch("src.services.capabilities.registry.resolve_k6_binary", return_value=None):
            CapabilityRegistry.invalidate()
            self.assertNotIn("perf_execution", ExecutorTaskWorker._supported_task_types())
        with patch("src.services.capabilities.registry.resolve_k6_binary", return_value="/runtime/bin/k6"):
            CapabilityRegistry.invalidate()
            self.assertIn("perf_execution", ExecutorTaskWorker._supported_task_types())
        CapabilityRegistry.invalidate()

    def test_running_perf_task_reports_no_available_perf_slot(self):
        from src.services.capabilities import CapabilityRegistry

        with (
            patch("src.services.capabilities.registry.resolve_k6_binary", return_value="/runtime/bin/k6"),
            patch.dict("os.environ", {"MANGO_CAPABILITIES_ENABLED": "perf", "MANGO_CAPACITY_PERF": "1"}, clear=False),
        ):
            CapabilityRegistry.invalidate()
            self.assertEqual(CapabilityRegistry.available_task_type_capacities()["perf_execution"], 1)
            self.assertTrue(CapabilityRegistry.acquire(["perf"]))
            try:
                self.assertEqual(CapabilityRegistry.available_task_type_capacities()["perf_execution"], 0)
            finally:
                CapabilityRegistry.release(["perf"])
                CapabilityRegistry.invalidate()

    async def test_execute_reports_result_from_reflection_handler(self):
        actuator_tasks = type("TaskApi", (), {})()
        actuator_tasks.running = AsyncMock(return_value={"code": 200, "data": {}})
        actuator_tasks.heartbeat = AsyncMock(return_value={"code": 200, "data": {}})
        actuator_tasks.result = AsyncMock(return_value={"code": 200, "data": {}})

        with (
            patch("src.services.executor_task_worker.HTTP.actuator_tasks", actuator_tasks),
            patch(
                "src.consumer.SocketConsumer.execute_executor_task",
                new=AsyncMock(return_value={"status": 1, "check_id": "check-1"}),
            ),
        ):
            await ExecutorTaskWorker._execute({
                "task_id": 12,
                "executor_connection_id": "connection-12",
                "retry_count": 2,
                "payload": {"func_name": "u_element_check", "func_args": {"id": 1}},
            })

        actuator_tasks.running.assert_awaited_once_with(12, connection_id="connection-12")
        actuator_tasks.result.assert_awaited_once()
        args = actuator_tasks.result.await_args.args
        kwargs = actuator_tasks.result.await_args.kwargs
        self.assertEqual(args[:2], (12, True))
        self.assertEqual(kwargs["result_data"]["check_id"], "check-1")
        self.assertEqual(kwargs["connection_id"], "connection-12")
        self.assertEqual(kwargs["attempt"], 2)

    async def test_web_ui_case_uses_case_parallel_slot_instead_of_live_workspace_slot(self):
        from src.services.capabilities import CapabilityRegistry

        actuator_tasks = type("TaskApi", (), {})()
        actuator_tasks.running = AsyncMock(return_value={"code": 200, "data": {}})
        actuator_tasks.heartbeat = AsyncMock(return_value={"code": 200, "data": {}})
        actuator_tasks.result = AsyncMock(return_value={"code": 200, "data": {}})

        with (
            patch("src.services.executor_task_worker.HTTP.actuator_tasks", actuator_tasks),
            patch(
                "src.consumer.SocketConsumer.execute_executor_task",
                new=AsyncMock(return_value={"status": 1}),
            ),
            patch.object(CapabilityRegistry, "required_capabilities", return_value=["web_ui"]),
            patch.object(CapabilityRegistry, "acquire", wraps=CapabilityRegistry.acquire) as acquire,
            patch(
                "src.services.ui.case_concurrency.SetConfig.get_web_parallel",
                return_value=2,
            ),
        ):
            await ExecutorTaskWorker._execute({
                "task_id": 121,
                "task_type": "ui_case",
                "payload": {"func_name": "u_case", "func_args": {}},
            })

        acquire.assert_not_called()
        self.assertEqual(UiCaseConcurrency.running(), 0)
        self.assertTrue(actuator_tasks.result.await_args.args[1])

    async def test_claimed_ui_case_can_consume_pre_reserved_parallel_slot(self):
        from src.services.capabilities import CapabilityRegistry

        actuator_tasks = type("TaskApi", (), {})()
        actuator_tasks.running = AsyncMock(return_value={"code": 200, "data": {}})
        actuator_tasks.heartbeat = AsyncMock(return_value={"code": 200, "data": {}})
        actuator_tasks.result = AsyncMock(return_value={"code": 200, "data": {}})

        with (
            patch("src.services.executor_task_worker.HTTP.actuator_tasks", actuator_tasks),
            patch(
                "src.consumer.SocketConsumer.execute_executor_task",
                new=AsyncMock(return_value={"status": 1}),
            ),
            patch.object(CapabilityRegistry, "required_capabilities", return_value=["web_ui"]),
            patch(
                "src.services.ui.case_concurrency.SetConfig.get_web_parallel",
                return_value=1,
            ),
        ):
            self.assertEqual(UiCaseConcurrency.reserve(1), 1)
            await ExecutorTaskWorker._execute({
                "task_id": 122,
                "task_type": "ui_case",
                "_ui_case_capacity_reserved": True,
                "payload": {"func_name": "u_case", "func_args": {}},
            })

        self.assertEqual(UiCaseConcurrency.running(), 0)
        self.assertTrue(actuator_tasks.result.await_args.args[1])

    async def test_task_runtime_config_is_scoped_to_current_execution(self):
        actuator_tasks = type("TaskApi", (), {})()
        actuator_tasks.running = AsyncMock(return_value={"code": 200, "data": {}})
        actuator_tasks.heartbeat = AsyncMock(return_value={"code": 200, "data": {}})
        actuator_tasks.result = AsyncMock(return_value={"code": 200, "data": {}})
        observed = {}

        async def execute(_func_name, _func_args):
            observed.update(get_task_ui_runtime_config())
            return {"status": 1}

        with (
            patch("src.services.executor_task_worker.HTTP.actuator_tasks", actuator_tasks),
            patch("src.consumer.SocketConsumer.execute_executor_task", side_effect=execute),
        ):
            await ExecutorTaskWorker._execute({
                "task_id": 120,
                "executor_connection_id": "connection-120",
                "payload": {
                    "func_name": "u_element_check",
                    "func_args": {
                        "runtime_config": {
                            "fixed_locator_retry_seconds": 17,
                            "smart_locator_timeout_seconds": 41,
                            "visual_locator_enabled": True,
                        },
                    },
                },
            })

        self.assertEqual(observed["fixed_locator_retry_seconds"], 17)
        self.assertEqual(observed["smart_locator_timeout_seconds"], 41)
        self.assertTrue(observed["visual_locator_enabled"])
        self.assertEqual(get_task_ui_runtime_config(), {})

    async def test_heartbeat_failure_stops_execution_and_reports_failure(self):
        actuator_tasks = type("TaskApi", (), {})()
        actuator_tasks.running = AsyncMock(return_value={"code": 200, "data": {}})
        actuator_tasks.result = AsyncMock(return_value={"code": 200, "data": {}})

        async def fail_heartbeat(_task_id, _cancel_event, _connection_id=None):
            await asyncio.sleep(0)
            raise RuntimeError("heartbeat failed")

        async def long_running(*_args):
            await asyncio.sleep(60)

        with (
            patch("src.services.executor_task_worker.HTTP.actuator_tasks", actuator_tasks),
            patch.object(ExecutorTaskWorker, "_heartbeat", side_effect=fail_heartbeat),
            patch(
                "src.consumer.SocketConsumer.execute_executor_task",
                side_effect=long_running,
            ),
        ):
            await ExecutorTaskWorker._execute({
                "task_id": 13,
                "payload": {"func_name": "u_element_check", "func_args": {"id": 1}},
            })

        actuator_tasks.result.assert_awaited_once()
        self.assertFalse(actuator_tasks.result.await_args.args[1])
        self.assertEqual(actuator_tasks.result.await_args.kwargs["error_code"], "executor_error")
        self.assertIn("heartbeat failed", actuator_tasks.result.await_args.kwargs["error_message"])
        await asyncio.sleep(0)
        leaked_waiters = [
            task for task in asyncio.all_tasks()
            if task is not asyncio.current_task()
            and task.get_name() == 'executor-task-cancel-waiter:13'
            and not task.done()
        ]
        self.assertEqual(leaked_waiters, [])

    async def test_result_submission_failure_is_saved_to_local_outbox(self):
        actuator_tasks = type("TaskApi", (), {})()
        actuator_tasks.result = AsyncMock(side_effect=RuntimeError('network down'))
        with (
            patch("src.services.executor_task_worker.HTTP.actuator_tasks", actuator_tasks),
            patch("src.services.executor_task_worker.log.error") as log_error,
        ):
            submitted = await ExecutorTaskWorker._submit_result(
                77,
                True,
                {'status': 1},
                None,
                None,
            )

        self.assertFalse(submitted)
        self.assertIn('任务最终结果发送失败', log_error.call_args.args[0])
        rows = ExecutorTaskResultOutbox.list_due(100)
        self.assertEqual(rows[0]['task_id'], 77)
        self.assertEqual(rows[0]['payload']['result_data']['status'], 1)

    async def test_business_failure_is_warning_after_server_confirmation(self):
        actuator_tasks = type("TaskApi", (), {})()
        actuator_tasks.result = AsyncMock(return_value={"code": 200, "data": {}})
        with (
            patch("src.services.executor_task_worker.HTTP.actuator_tasks", actuator_tasks),
            patch("src.services.executor_task_worker.log.warning") as log_warning,
            patch("src.services.executor_task_worker.log.error") as log_error,
        ):
            submitted = await ExecutorTaskWorker._submit_result(
                771,
                False,
                {'status': 0},
                'business_failed',
                '断言失败，页面未包含预期文本',
            )

        self.assertTrue(submitted)
        self.assertIn('业务结果未通过', log_warning.call_args.args[0])
        log_error.assert_not_called()

    async def test_cancel_event_wins_even_when_waiter_is_not_in_done_set(self):
        actuator_tasks = type("TaskApi", (), {})()
        actuator_tasks.running = AsyncMock(return_value={"code": 200, "data": {}})
        actuator_tasks.result = AsyncMock(return_value={"code": 200, "data": {}})

        async def cancel_immediately(_task_id, cancel_event, _connection_id=None):
            cancel_event.set()

        async def long_running(*_args):
            await asyncio.sleep(60)

        with (
            patch("src.services.executor_task_worker.HTTP.actuator_tasks", actuator_tasks),
            patch.object(ExecutorTaskWorker, "_heartbeat", side_effect=cancel_immediately),
            patch(
                "src.consumer.SocketConsumer.execute_executor_task",
                side_effect=long_running,
            ),
        ):
            await asyncio.wait_for(ExecutorTaskWorker._execute({
                "task_id": 14,
                "payload": {"func_name": "u_element_check", "func_args": {"id": 1}},
            }), timeout=3)

        actuator_tasks.result.assert_awaited_once()
        self.assertFalse(actuator_tasks.result.await_args.args[1])
        self.assertEqual(actuator_tasks.result.await_args.kwargs["error_code"], "cancelled")

    async def test_unsupported_protocol_version_becomes_terminal_failure(self):
        actuator_tasks = type("TaskApi", (), {})()
        actuator_tasks.running = AsyncMock(return_value={"code": 200, "data": {}})
        actuator_tasks.heartbeat = AsyncMock(return_value={"code": 200, "data": {}})
        actuator_tasks.result = AsyncMock(return_value={"code": 200, "data": {}})
        with patch("src.services.executor_task_worker.HTTP.actuator_tasks", actuator_tasks):
            await ExecutorTaskWorker._execute({
                "task_id": 79,
                "executor_connection_id": "connection-79",
                "payload": {
                    "schema_version": 2,
                    "func_name": "u_element_check",
                    "func_args": {"id": 1},
                },
            })

        actuator_tasks.result.assert_awaited_once()
        self.assertEqual(
            actuator_tasks.result.await_args.kwargs["error_code"],
            "unsupported_schema_version",
        )

    async def test_outbox_result_is_deleted_after_retry_success(self):
        ExecutorTaskResultOutbox.upsert(78, {
            'success': True,
            'result_data': {'status': 1},
            'error_code': None,
            'error_message': None,
        })
        actuator_tasks = type("TaskApi", (), {})()
        actuator_tasks.result = AsyncMock(return_value={'code': 200, 'data': {}})
        with patch("src.services.executor_task_worker.HTTP.actuator_tasks", actuator_tasks):
            await ExecutorTaskWorker._flush_result_outbox()

        self.assertEqual(ExecutorTaskResultOutbox.list_due(100), [])

    async def test_stale_outbox_result_is_deleted_after_terminal_rejection(self):
        ExecutorTaskResultOutbox.upsert(780, {
            'success': False,
            'result_data': {},
            'error_code': 'executor_error',
            'error_message': 'network down',
            'connection_id': 'expired-connection',
        })
        actuator_tasks = type("TaskApi", (), {})()
        actuator_tasks.result = AsyncMock(
            side_effect=ApiError('执行器任务状态或领取关系已失效，请停止执行该任务', status_code=1162),
        )
        with patch("src.services.executor_task_worker.HTTP.actuator_tasks", actuator_tasks):
            await ExecutorTaskWorker._flush_result_outbox()

        rows = ExecutorTaskResultOutbox.list_due(100)
        self.assertNotIn(780, [row['task_id'] for row in rows])

    def test_task_api_rejects_http_success_with_business_error_code(self):
        with self.assertRaises(ApiError) as context:
            ActuatorTaskApi._require_success({
                'code': 300,
                'msg': '任务租约已失效',
                'data': None,
            })

        self.assertIn('任务租约已失效', str(context.exception))

    def test_task_api_accepts_platform_success_response(self):
        response = {'code': 200, 'msg': '成功', 'data': {'tasks': []}}
        self.assertIs(ActuatorTaskApi._require_success(response), response)

    def test_claim_failure_uses_bounded_exponential_backoff(self):
        self.assertEqual(ExecutorTaskWorker._retry_backoff_seconds(1), 2)
        self.assertEqual(ExecutorTaskWorker._retry_backoff_seconds(2), 4)
        self.assertEqual(ExecutorTaskWorker._retry_backoff_seconds(5), 30)
        self.assertEqual(ExecutorTaskWorker._retry_backoff_seconds(20), 30)

    async def test_stale_registration_error_requests_websocket_reconnect(self):
        with patch(
            "src.network.web_socket.websocket_client.WebSocketClient.reconnect_if_authenticated",
            new=AsyncMock(return_value=True),
        ) as reconnect:
            recovered = await ExecutorTaskWorker._recover_stale_registration(
                ApiError("目标执行器用户不存在或当前不可用", status_code=1165),
            )

        self.assertTrue(recovered)
        reconnect.assert_awaited_once_with("目标执行器用户不存在或当前不可用")

    async def test_other_claim_error_does_not_reconnect_websocket(self):
        with patch(
            "src.network.web_socket.websocket_client.WebSocketClient.reconnect_if_authenticated",
            new=AsyncMock(),
        ) as reconnect:
            recovered = await ExecutorTaskWorker._recover_stale_registration(
                ApiError("临时服务异常", status_code=500),
            )

        self.assertFalse(recovered)
        reconnect.assert_not_awaited()

    def test_task_metadata_uses_task_type_and_optional_business_ids(self):
        metadata = ExecutorTaskWorker._task_metadata({
            'task_type': 'ui_case',
            'payload': {
                'func_name': 'u_case',
                'func_args': {
                    'id': 4,
                    'execution_id': 'execution-4',
                    'slot_id': 'slot-1',
                },
            },
        })
        self.assertEqual(metadata['task_type'], 'ui_case')
        self.assertEqual(metadata['func_name'], 'u_case')
        self.assertEqual(metadata['case_id'], 4)
        self.assertEqual(metadata['execution_id'], 'execution-4')
        self.assertEqual(metadata['slot_id'], 'slot-1')

    def test_executor_task_context_contains_task_and_connection(self):
        token = set_executor_task_id(
            91,
            'connection-91',
            task_type='ui_case',
            case_id=4,
            execution_id='execution-91',
        )
        try:
            self.assertEqual(get_executor_task_context(), (91, 'connection-91'))
            self.assertEqual(get_executor_task_log_context(), {
                'task_id': 91,
                'task_type': 'ui_case',
                'case_id': 4,
                'execution_id': 'execution-91',
                'connection_id': 'connection-91',
            })
        finally:
            reset_executor_task_id(token)
        self.assertEqual(get_executor_task_context(), (None, None))
        self.assertEqual(get_executor_task_log_context(), {})

    async def test_executor_task_decorator_does_not_swallow_business_error(self):
        @async_error_handle()
        async def fail_inside_task():
            raise RuntimeError('executor task failed')

        token = set_executor_task_id(92, 'connection-92')
        try:
            with self.assertRaisesRegex(RuntimeError, 'executor task failed'):
                await fail_inside_task()
        finally:
            reset_executor_task_id(token)

    async def test_worker_reports_draining_on_start_and_shutdown(self):
        actuator_tasks = type("TaskApi", (), {})()
        actuator_tasks.draining = AsyncMock(return_value={"code": 200, "data": {}})
        actuator_tasks.claim = AsyncMock(side_effect=asyncio.CancelledError)

        with patch("src.services.executor_task_worker.HTTP.actuator_tasks", actuator_tasks):
            with self.assertRaises(asyncio.CancelledError):
                await ExecutorTaskWorker.run()

        self.assertEqual(actuator_tasks.draining.await_count, 2)
        self.assertEqual(actuator_tasks.draining.await_args_list[0].args, (False,))
        self.assertEqual(actuator_tasks.draining.await_args_list[1].args, (True,))

    async def test_shutdown_interrupts_running_task_after_grace_period(self):
        actuator_tasks = type("TaskApi", (), {})()
        actuator_tasks.running = AsyncMock(return_value={"code": 200, "data": {}})
        actuator_tasks.heartbeat = AsyncMock(return_value={"code": 200, "data": {}})
        actuator_tasks.result = AsyncMock(return_value={"code": 200, "data": {}})

        async def pending_execution(*_args, **_kwargs):
            await asyncio.sleep(60)

        with (
            patch("src.services.executor_task_worker.HTTP.actuator_tasks", actuator_tasks),
            patch.object(ExecutorTaskWorker, "DRAIN_GRACE_SECONDS", 0.01),
            patch("src.consumer.SocketConsumer.execute_executor_task", side_effect=pending_execution),
        ):
            running = asyncio.create_task(ExecutorTaskWorker._execute({
                "task_id": 93,
                "executor_connection_id": "connection-93",
                "payload": {"func_name": "u_element_check", "func_args": {}},
            }))
            ExecutorTaskWorker._running_tasks.add(running)
            await asyncio.sleep(0)
            await ExecutorTaskWorker._drain_running_tasks()

        self.assertTrue(running.cancelled())
        self.assertEqual(actuator_tasks.result.await_args.kwargs["error_code"], "executor_draining")


if __name__ == "__main__":
    unittest.main()
