import asyncio
import time
import traceback

from pydantic import BaseModel

from src.network import HTTP
from src.network.http.apis.base import ApiError
from src.storage.sqlite import ExecutorTaskResultOutbox, StepHealReportOutbox
from src.tools.executor_task_context import (
    format_executor_task_log,
    reset_executor_task_id,
    set_executor_task_id,
)
from src.tools.log_collector import log
from src.services.runtime_config import reset_task_ui_runtime_config, set_task_ui_runtime_config
from src.services.ui.case_concurrency import UiCaseConcurrency
from src.services.system_error_reporter import ActuatorSystemErrorReporter


class ExecutorTaskWorker:
    """以 HTTP 领取任务，WebSocket 仅负责缩短唤醒延迟。"""

    POLL_INTERVAL_SECONDS = 1.0
    HEARTBEAT_INTERVAL_SECONDS = 10.0
    DRAIN_GRACE_SECONDS = 5.0
    MAX_CONCURRENT_TASKS = 5
    _wake_event = asyncio.Event()
    _running_tasks: set[asyncio.Task] = set()
    MAX_RETRY_BACKOFF_SECONDS = 30.0
    STALE_REGISTRATION_ERROR_CODE = 1165
    RUNTIME_CONFIG_REFRESH_SECONDS = 60
    _next_runtime_config_refresh_at = 0.0

    @staticmethod
    def _supported_task_types() -> list[str]:
        from src.services.capabilities import CapabilityRegistry

        return CapabilityRegistry.supported_task_types()

    @classmethod
    def wake(cls) -> None:
        cls._wake_event.set()

    @classmethod
    async def run(cls) -> None:
        consecutive_claim_failures = 0
        try:
            try:
                await HTTP.actuator_tasks.draining(False)
            except Exception as error:
                await ActuatorSystemErrorReporter.report(error, 'services/executor_task_worker:run')
                # 启动阶段 WebSocket 连接可能尚未登记完成，不能因此终止轮询工作线程。
                log.warning(f'执行器启动时取消 draining 失败，将继续领取任务：{error}')
            while True:
                reserved_ui_cases = 0
                try:
                    from src.services.capabilities import CapabilityRegistry

                    now = time.monotonic()
                    if now >= cls._next_runtime_config_refresh_at:
                        cls._next_runtime_config_refresh_at = now + cls.RUNTIME_CONFIG_REFRESH_SECONDS
                        try:
                            await HTTP.system.refresh_runtime_config()
                        except Exception as error:
                            await ActuatorSystemErrorReporter.report(error, 'services/executor_task_worker:run')
                            log.warning(f'刷新执行器运行配置失败，继续使用当前值：{error}')

                    await cls._flush_result_outbox()
                    await cls._flush_step_heal_report_outbox()
                    cls._running_tasks = {task for task in cls._running_tasks if not task.done()}
                    capacity = cls._max_concurrent_tasks() - len(cls._running_tasks)
                    if capacity <= 0:
                        await cls._wait_for_wake()
                        continue
                    task_type_capacities = CapabilityRegistry.available_task_type_capacities()
                    reserved_ui_cases = UiCaseConcurrency.reserve(
                        min(capacity, int(task_type_capacities.get('ui_case') or 0)),
                    )
                    task_type_capacities['ui_case'] = reserved_ui_cases
                    response = await HTTP.actuator_tasks.claim(
                        capacity=capacity,
                        supported_task_types=cls._supported_task_types(),
                        protocol_versions=cls._protocol_versions(),
                        capability_capacities=CapabilityRegistry.capability_capacities(),
                        task_type_capacities=task_type_capacities,
                    )
                    tasks = cls._response_data(response).get('tasks') or []
                    consecutive_claim_failures = 0
                    if tasks:
                        for task in tasks:
                            log.info(cls._task_log_message('执行器已领取任务', task))
                            has_reserved_ui_case = (
                                reserved_ui_cases > 0 and cls._is_ui_case_task(task)
                            )
                            if has_reserved_ui_case:
                                task['_ui_case_capacity_reserved'] = True
                            handle = asyncio.create_task(
                                cls._execute(task),
                                name=f'executor-task:{task.get("task_id")}',
                            )
                            if has_reserved_ui_case:
                                reserved_ui_cases -= 1
                            cls._running_tasks.add(handle)
                            handle.add_done_callback(cls._running_tasks.discard)
                        if reserved_ui_cases:
                            UiCaseConcurrency.release(reserved_ui_cases)
                            reserved_ui_cases = 0
                        # 让新任务先登记能力和 Case 容量，再发起下一轮领取，避免瞬间超领。
                        await asyncio.sleep(0)
                        continue
                    if reserved_ui_cases:
                        UiCaseConcurrency.release(reserved_ui_cases)
                        reserved_ui_cases = 0
                except asyncio.CancelledError:
                    if reserved_ui_cases:
                        UiCaseConcurrency.release(reserved_ui_cases)
                    raise
                except Exception as error:
                    await ActuatorSystemErrorReporter.report(error, 'services/executor_task_worker:run')
                    if reserved_ui_cases:
                        UiCaseConcurrency.release(reserved_ui_cases)
                    registration_reconnecting = await cls._recover_stale_registration(error)
                    if registration_reconnecting:
                        consecutive_claim_failures = 0
                        await asyncio.sleep(cls.POLL_INTERVAL_SECONDS)
                        continue
                    consecutive_claim_failures += 1
                    retry_seconds = cls._retry_backoff_seconds(consecutive_claim_failures)
                    log.warning(f'领取执行器任务失败，{retry_seconds:g}秒后重试：{error}')
                    await asyncio.sleep(retry_seconds)
                    continue
                await cls._wait_for_wake()
        finally:
            try:
                await HTTP.actuator_tasks.draining(True)
            except Exception as error:
                await ActuatorSystemErrorReporter.report(error, 'services/executor_task_worker:run')
                log.warning(f'执行器退出时上报 draining 失败，将由租约回收兜底：{error}')
            await cls._drain_running_tasks()

    @classmethod
    async def _drain_running_tasks(cls) -> None:
        running = {task for task in cls._running_tasks if not task.done()}
        if not running:
            return
        done, pending = await asyncio.wait(running, timeout=cls.DRAIN_GRACE_SECONDS)
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
        cls._running_tasks = {task for task in cls._running_tasks if not task.done()}

    @classmethod
    async def _wait_for_wake(cls) -> None:
        cls._wake_event.clear()
        try:
            await asyncio.wait_for(cls._wake_event.wait(), timeout=cls.POLL_INTERVAL_SECONDS)
        except asyncio.TimeoutError:
            pass

    @classmethod
    async def _flush_step_heal_report_outbox(cls) -> None:
        for row in StepHealReportOutbox.list_due():
            try:
                await HTTP.ui_page_step.save_heal_report(row['payload'])
                StepHealReportOutbox.delete(row['id'])
                log.info(f'页面步骤自愈记录补传成功：trace_id={row["trace_id"]}')
            except Exception as error:
                await ActuatorSystemErrorReporter.report(error, 'services/executor_task_worker:_flush_step_heal_report_outbox')
                StepHealReportOutbox.mark_failed(row['id'], row['retry_count'], error)
                log.debug(f'页面步骤自愈记录补传失败：trace_id={row["trace_id"]}，原因={error}')
                break

    @classmethod
    def _retry_backoff_seconds(cls, consecutive_failures: int) -> float:
        return min(
            cls.MAX_RETRY_BACKOFF_SECONDS,
            float(2 ** min(max(1, int(consecutive_failures)), 5)),
        )

    @classmethod
    async def _recover_stale_registration(cls, error: Exception) -> bool:
        if not (
            isinstance(error, ApiError)
            and error.status_code == cls.STALE_REGISTRATION_ERROR_CODE
        ):
            return False
        from src.network.web_socket.websocket_client import WebSocketClient

        return await WebSocketClient.reconnect_if_authenticated(str(error))

    @classmethod
    async def _execute(cls, task: dict) -> None:
        from src.services.capabilities import CapabilityRegistry

        task_id = int(task['task_id'])
        connection_id = task.get('executor_connection_id')
        attempt = int(task.get('retry_count') or 0)
        payload = task.get('payload') or {}
        func_name = payload.get('func_name')
        func_args = payload.get('func_args')
        task_context_token = set_executor_task_id(
            task_id,
            connection_id,
            **cls._task_metadata(task, payload),
        )
        runtime_config_token = set_task_ui_runtime_config(
            func_args.get('runtime_config') if isinstance(func_args, dict) else None,
        )
        required_capabilities = CapabilityRegistry.required_capabilities(task.get('task_type'), payload)
        is_ui_case = cls._is_ui_case_task(task)
        case_capacity_acquired = bool(task.pop('_ui_case_capacity_reserved', False))
        capability_acquired = False
        heartbeat_task = None
        execution_task = None
        cancel_waiter = None
        try:
            log.debug(format_executor_task_log(
                '执行器任务准备执行',
                retry_count=attempt,
                required_capabilities=','.join(required_capabilities) or '-',
            ))
            if is_ui_case and not case_capacity_acquired:
                case_capacity_acquired = UiCaseConcurrency.acquire()
                if not case_capacity_acquired:
                    await cls._submit_result(
                        task_id,
                        False,
                        {},
                        'ui_case_capacity_exhausted',
                        'UI用例并发已达到执行器配置上限，请稍后重试',
                        connection_id,
                        attempt,
                    )
                    return
            acquired_capabilities = required_capabilities
            if is_ui_case and required_capabilities == ['web_ui']:
                # Web Case 使用 web_parallel 共享计数；web_ui=1 保留给实时工作台资源。
                acquired_capabilities = []
            if acquired_capabilities:
                capability_acquired = CapabilityRegistry.acquire(acquired_capabilities)
                if not capability_acquired:
                    await cls._submit_result(
                        task_id,
                        False,
                        {},
                        'capability_capacity_exhausted',
                        f'执行器能力不可用或容量已满：{",".join(acquired_capabilities)}',
                        connection_id,
                        attempt,
                    )
                    return
            schema_version = int(payload.get('schema_version') or 1)
            if schema_version != 1:
                await cls._submit_result(
                    task_id,
                    False,
                    {},
                    'unsupported_schema_version',
                    f'执行器不支持任务协议版本：{schema_version}',
                    connection_id,
                    attempt,
                )
                return
            await HTTP.actuator_tasks.running(task_id, connection_id=connection_id)
            log.info(format_executor_task_log('执行器任务开始执行', retry_count=attempt))
            cancel_event = asyncio.Event()
            heartbeat_task = asyncio.create_task(
                cls._heartbeat(task_id, cancel_event, connection_id),
                name=f'executor-task-heartbeat:{task_id}',
            )
            from src.consumer import SocketConsumer

            execution_task = asyncio.create_task(
                SocketConsumer.execute_executor_task(func_name, func_args),
                name=f'executor-task-execution:{task_id}',
            )
            cancel_waiter = asyncio.create_task(
                cancel_event.wait(),
                name=f'executor-task-cancel-waiter:{task_id}',
            )
            done, _ = await asyncio.wait(
                {execution_task, cancel_waiter, heartbeat_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            if heartbeat_task in done and not cancel_event.is_set():
                # 心跳异常意味着任务租约已经不再可靠，立即停止本地执行，
                # 避免服务端恢复任务后两个执行实例同时操作同一浏览器。
                await heartbeat_task
            if cancel_event.is_set():
                execution_task.cancel()
                await asyncio.gather(execution_task, return_exceptions=True)
                await cls._submit_result(
                    task_id,
                    False,
                    {},
                    'cancelled',
                    '用户已取消任务',
                    connection_id,
                    attempt,
                )
                log.info(format_executor_task_log('执行器任务已取消'))
                return
            cancel_waiter.cancel()
            await asyncio.gather(cancel_waiter, return_exceptions=True)
            result = await execution_task
            success, error_message = cls._execution_outcome(result)
            await cls._submit_result(
                task_id,
                success,
                cls._json_result(result),
                None if success else 'business_failed',
                error_message,
                connection_id,
                attempt,
            )
            log.debug(format_executor_task_log(
                '执行器任务业务处理结束', success=success, error_code=None if success else 'business_failed',
            ))
        except asyncio.CancelledError:
            try:
                await cls._submit_result(
                    task_id,
                    False,
                    {},
                    'executor_draining',
                    '执行器正常退出，运行中的任务已中断',
                    connection_id,
                    attempt,
                )
            except Exception as report_error:
                await ActuatorSystemErrorReporter.report(report_error, 'services/executor_task_worker:_execute')
                log.error(format_executor_task_log(
                    '执行器退出时保存中断结果失败', error=report_error,
                ))
            raise
        except Exception as error:
            error_message = str(error) or type(error).__name__
            trace = traceback.format_exc()
            await ActuatorSystemErrorReporter.report(
                error,
                f'executor-task:{func_name or task.get("task_type") or "unknown"}',
                traceback_text=trace,
            )
            log.error(format_executor_task_log(
                '执行器任务发生系统异常', error=error_message, detail=trace,
            ))
            try:
                await cls._submit_result(
                    task_id,
                    False,
                    {},
                    'executor_error',
                    error_message,
                    connection_id,
                    attempt,
                )
            except Exception as report_error:
                await ActuatorSystemErrorReporter.report(report_error, 'services/executor_task_worker:_execute')
                log.error(format_executor_task_log(
                    '执行器任务异常结果回传失败', error=report_error,
                ))
        finally:
            if execution_task and not execution_task.done():
                execution_task.cancel()
                await asyncio.gather(execution_task, return_exceptions=True)
            if cancel_waiter and not cancel_waiter.done():
                cancel_waiter.cancel()
                await asyncio.gather(cancel_waiter, return_exceptions=True)
            if heartbeat_task:
                heartbeat_task.cancel()
                await asyncio.gather(heartbeat_task, return_exceptions=True)
            if capability_acquired:
                CapabilityRegistry.release(acquired_capabilities)
            if case_capacity_acquired:
                UiCaseConcurrency.release()
            reset_executor_task_id(task_context_token)
            reset_task_ui_runtime_config(runtime_config_token)

    @classmethod
    def _max_concurrent_tasks(cls) -> int:
        return max(cls.MAX_CONCURRENT_TASKS, UiCaseConcurrency.capacity())

    @staticmethod
    def _is_ui_case_task(task: dict) -> bool:
        payload = task.get('payload') if isinstance(task.get('payload'), dict) else {}
        return str(task.get('task_type') or '') == 'ui_case' or payload.get('func_name') == 'u_case'

    @staticmethod
    def _task_metadata(task: dict, payload: dict | None = None) -> dict:
        payload = payload or (task.get('payload') if isinstance(task.get('payload'), dict) else {})
        func_name = payload.get('func_name')
        func_args = payload.get('func_args') if isinstance(payload.get('func_args'), dict) else {}
        metadata = {
            'task_type': task.get('task_type'),
            'func_name': func_name,
        }
        for key in (
            'execution_id', 'slot_id', 'workspace_id', 'case_id', 'page_step_id',
            'element_id', 'test_suite_id', 'test_suite', 'time_task_id', 'trigger_id',
        ):
            if func_args.get(key) not in (None, ''):
                metadata[key] = func_args[key]
        business_id = func_args.get('id')
        if func_name == 'u_case' and 'case_id' not in metadata:
            metadata['case_id'] = business_id
        elif func_name in {'u_page_step', 'u_page_steps'} and 'page_step_id' not in metadata:
            metadata['page_step_id'] = business_id
        elif func_name in {'u_element_check', 'u_element'} and 'element_id' not in metadata:
            metadata['element_id'] = business_id
        elif business_id is not None:
            metadata['business_id'] = business_id
        return {key: value for key, value in metadata.items() if value not in (None, '')}

    @classmethod
    def _task_log_message(cls, message: str, task: dict) -> str:
        fields = {'task_id': task.get('task_id'), **cls._task_metadata(task)}
        fields['retry_count'] = int(task.get('retry_count') or 0)
        detail = ', '.join(
            f'{key}={value}' for key, value in fields.items() if value not in (None, '')
        )
        return f'{message} [{detail}]'

    @staticmethod
    def _protocol_versions() -> dict[str, int]:
        from src.services.capabilities import CapabilityRegistry

        return CapabilityRegistry.protocol_versions()

    @classmethod
    async def _submit_result(
        cls,
        task_id: int,
        success: bool,
        result_data: dict | list,
        error_code: str | None,
        error_message: str | None,
        connection_id: str | None = None,
        attempt: int = 0,
    ) -> bool:
        def task_log(message: str, **extra) -> str:
            return format_executor_task_log(message, task_id=task_id, **extra)

        payload = {
            'success': bool(success),
            'result_data': result_data,
            'error_code': error_code,
            'error_message': error_message,
            'connection_id': connection_id,
            'attempt': int(attempt),
        }
        # 先落本地再提交，保证网络中断或进程退出时最终结果仍可重放。
        log.debug(task_log('准备保存任务最终结果到本地重试队列'))
        try:
            ExecutorTaskResultOutbox.upsert(task_id, payload)
        except Exception as error:
            await ActuatorSystemErrorReporter.report(error, 'services/executor_task_worker:_submit_result')
            log.error(task_log(
                '任务最终结果写入本地重试队列失败', error=error,
            ))
            raise
        log.debug(task_log('任务最终结果已保存到本地重试队列'))
        try:
            log.debug(task_log('开始向服务端提交任务最终结果'))
            await HTTP.actuator_tasks.result(
                task_id,
                payload['success'],
                result_data=payload['result_data'],
                error_code=payload['error_code'],
                error_message=payload['error_message'],
                connection_id=payload['connection_id'],
                attempt=payload['attempt'],
            )
        except Exception as error:
            await ActuatorSystemErrorReporter.report(error, 'services/executor_task_worker:_submit_result')
            try:
                ExecutorTaskResultOutbox.upsert(task_id, payload, error)
            except Exception as save_error:
                await ActuatorSystemErrorReporter.report(save_error, 'services/executor_task_worker:_submit_result')
                log.error(task_log(
                    '任务最终结果发送及本地保存均失败',
                    send_error=error,
                    save_error=save_error,
                ))
                raise
            log.error(task_log(
                '任务最终结果发送失败，已保留在本地重试队列', error=error,
            ))
            return False
        try:
            ExecutorTaskResultOutbox.delete_by_task_id(task_id)
        except Exception as error:
            await ActuatorSystemErrorReporter.report(error, 'services/executor_task_worker:_submit_result')
            log.error(task_log(
                '服务端已确认任务结果，但清理本地重试记录失败', error=error,
            ))
            raise
        log.debug(task_log('服务端已确认任务结果，本地重试记录已清理'))
        if success:
            log.info(task_log('执行器任务完成，服务端已确认最终结果'))
        else:
            log.warning(task_log(
                '执行器任务完成，业务结果未通过',
                error_code=error_code,
                error_message=error_message,
            ))
        return True

    @classmethod
    async def _flush_result_outbox(cls) -> None:
        for row in ExecutorTaskResultOutbox.list_due():
            try:
                payload = row['payload']
                log.debug(
                    f'开始重试提交任务最终结果 [task_id={row["task_id"]}, '
                    f'retry_count={row["retry_count"]}]'
                )
                await HTTP.actuator_tasks.result(
                    row['task_id'],
                    payload['success'],
                    result_data=payload.get('result_data'),
                    error_code=payload.get('error_code'),
                    error_message=payload.get('error_message'),
                    connection_id=payload.get('connection_id'),
                    attempt=int(payload.get('attempt') or 0),
                )
            except Exception as error:
                await ActuatorSystemErrorReporter.report(error, 'services/executor_task_worker:_flush_result_outbox')
                if cls._is_terminal_result_rejection(error):
                    ExecutorTaskResultOutbox.delete(row['id'])
                    log.error(
                        f'执行器任务结果已失效，停止本地重试：'
                        f'task_id={row["task_id"]}，error={error}'
                    )
                    continue
                ExecutorTaskResultOutbox.mark_failed(row['id'], row['retry_count'], error)
                log.error(
                    f'重试提交任务最终结果失败 [task_id={row["task_id"]}, '
                    f'retry_count={row["retry_count"]}, error={error}]'
                )
                continue
            ExecutorTaskResultOutbox.delete(row['id'])
            log.info(f'本地任务最终结果重试成功 [task_id={row["task_id"]}]')

    @staticmethod
    def _is_terminal_result_rejection(error: Exception) -> bool:
        """任务不存在或领取关系失效后，旧连接的结果不可能再次提交成功。"""
        return isinstance(error, ApiError) and error.status_code in {1160, 1162}

    @classmethod
    async def _heartbeat(
        cls,
        task_id: int,
        cancel_event: asyncio.Event,
        connection_id: str | None = None,
    ) -> None:
        while True:
            await asyncio.sleep(cls.HEARTBEAT_INTERVAL_SECONDS)
            log.debug(format_executor_task_log('发送任务心跳'))
            response = await HTTP.actuator_tasks.heartbeat(
                task_id,
                connection_id=connection_id,
            )
            data = cls._response_data(response)
            if data.get('cancel_requested'):
                log.info(format_executor_task_log('服务端请求取消任务'))
                cancel_event.set()
                return

    @staticmethod
    def _response_data(response: dict) -> dict:
        data = response.get('data') if isinstance(response, dict) else None
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _json_result(value):
        if value is None:
            return {}
        if isinstance(value, BaseModel):
            return value.model_dump(mode='json')
        if isinstance(value, (dict, list)):
            return value
        return {'value': str(value)}

    @staticmethod
    def _execution_outcome(value) -> tuple[bool, str | None]:
        if isinstance(value, BaseModel):
            value = value.model_dump(mode='json')
        if isinstance(value, dict) and 'status' in value:
            success = value.get('status') in (1, True, 'success', 'passed')
            return success, None if success else str(value.get('error_message') or '任务执行失败')
        return True, None
