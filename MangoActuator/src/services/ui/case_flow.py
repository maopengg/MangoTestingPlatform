# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2024-04-26 10:53
# @Author : 毛鹏

from src.services.system_error_reporter import ActuatorSystemErrorReporter
import asyncio
import json
import time
import traceback
import uuid

from mangotools.enums import ClientTypeEnum
from mangotools.enums import TestCaseTypeEnum
from mangotools.contracts import TaskPullRequest
from mangoautomation.models import CaseModel
from src.network import socket_conn
from src.services.runtime.session import AutomationSessionManager
from src.services.ui.test_case import TestCase
from src.services.ui.case_concurrency import UiCaseConcurrency
from src.services.task_pull_failure import TaskPullFailureReporter
from src.settings import settings
from src.storage.sqlite import ExecutionCaseQueue, ExecutionCaseQueueFull
from src.tools.decorator.memory import async_memory
from src.tools.debug_case_file import save_ui_debug_payload
from src.tools.json_tools import json_dumps
from src.tools.log_collector import log
from src.tools.send_global_msg import send_global_msg
from src.tools.execution_activity import ExecutionActivity, execution_identity
from src.tools.set_config import SetConfig


class CaseFlow:
    ACTIVE_PULL_INTERVAL = 5
    EMPTY_PULL_INTERVAL = 10
    running_tasks = 0
    parent = None
    web_runtime = None
    running = True
    _queue_recovered = False
    _last_task_pull_time = 0.0
    _last_task_received_time = 0.0
    _task_pull_interval = ACTIVE_PULL_INTERVAL
    _force_pull = False
    _http_pull_disabled = False
    _running_task_handles: dict[int, tuple[int | None, asyncio.Task]] = {}

    @classmethod
    async def process_tasks(cls):
        cls.recover_queue()

        while cls.running:
            try:
                await asyncio.sleep(0.1)
                if (
                        ExecutionCaseQueue.pending_count(ExecutionCaseQueue.TYPE_UI)
                        and UiCaseConcurrency.acquire()
                ):
                    queue_item = ExecutionCaseQueue.fetch_next(ExecutionCaseQueue.TYPE_UI)
                    if not queue_item:
                        UiCaseConcurrency.release()
                        continue
                    try:
                        case_model = CaseModel(**json.loads(queue_item['payload']))
                    except Exception as error:
                        await ActuatorSystemErrorReporter.report(error, 'services/ui/case_flow:process_tasks')
                        UiCaseConcurrency.release()
                        ExecutionCaseQueue.mark_error(queue_item['id'], error)
                        ExecutionCaseQueue.delete(queue_item['id'])
                        log.error(
                            f'UI本地执行队列任务反序列化失败，已删除，queue_id={queue_item["id"]}，'
                            f'失败详情：{error}，失败明细：{traceback.format_exc()}'
                        )
                        continue
                    cls.running_tasks += 1
                    task = asyncio.create_task(cls.execute_task(queue_item['id'], case_model))
                    task.add_done_callback(lambda _task: UiCaseConcurrency.release())
                    cls._running_task_handles[queue_item['id']] = (case_model.test_suite_id, task)
                await cls.maybe_get_case_task()
            except asyncio.CancelledError:
                raise
            except Exception as error:
                await ActuatorSystemErrorReporter.report(error, 'services/ui/case_flow:process_tasks')
                log.error(
                    f'UI用例调度循环异常，调度器继续运行，类型：{type(error)}，'
                    f'失败详情：{error}，失败明细：{traceback.format_exc()}'
                )
                await asyncio.sleep(1)

    @classmethod
    async def maybe_get_case_task(cls):
        from src.services.capabilities import CapabilityRegistry

        if not any(CapabilityRegistry.ready(code) for code in ("web_ui", "android_ui", "ios_ui")):
            return
        if not settings.IS_OPEN:
            return
        queue_count = ExecutionCaseQueue.count(ExecutionCaseQueue.TYPE_UI)
        queue_limit = ExecutionCaseQueue.queue_limit(ExecutionCaseQueue.TYPE_UI)
        if queue_count >= queue_limit:
            return
        if not cls._force_pull and queue_count > cls.refill_trigger(queue_limit):
            return
        now = time.time()
        if cls._last_task_pull_time and cls._last_task_received_time <= cls._last_task_pull_time:
            cls._task_pull_interval = cls.EMPTY_PULL_INTERVAL
        if now - cls._last_task_pull_time < cls._task_pull_interval:
            return
        await cls.get_case_task()
        cls._force_pull = False
        cls._last_task_pull_time = now

    @classmethod
    async def get_case_task(cls):
        if await cls.pull_case_task_by_http():
            return
        await cls.get_case_task_by_websocket()

    @classmethod
    async def pull_case_task_by_http(cls) -> bool:
        if cls._http_pull_disabled:
            return False
        try:
            from src.network import HTTP
            queue_limit = ExecutionCaseQueue.queue_limit(ExecutionCaseQueue.TYPE_UI)
            queue_count = ExecutionCaseQueue.count(ExecutionCaseQueue.TYPE_UI)
            capacity = queue_limit - queue_count
            if capacity <= 0:
                return True
            batch_size = min(5, capacity)
            message_id = str(uuid.uuid4())
            resp = await HTTP.actuator_tasks.pull(
                message_id=message_id,
                task_type=ExecutionCaseQueue.TYPE_UI,
                capacity=batch_size,
                local_queue_size=queue_count,
                max_queue_size=queue_limit,
            )
            TaskPullFailureReporter.recovered('UI')
            if resp.get('code') != 200:
                return False
            data = resp.get('data') if isinstance(resp, dict) else {}
            tasks = data.get('tasks') if isinstance(data, dict) else []
            if not tasks:
                return True
            accepted, rejected = ExecutionCaseQueue.bulk_insert(
                ExecutionCaseQueue.TYPE_UI,
                tasks,
                source_message_id=message_id,
            )
            if rejected:
                msg = f'UI本地执行队列拒绝入队 {len(rejected)} 条任务，请检查队列容量配置'
                log.warning(f'{msg}，详情：{rejected[:3]}')
                send_global_msg(msg)
            ack_items = [
                {'dispatch_id': item.get('dispatch_id'), 'status': 'accepted'}
                for item in accepted
            ] + [
                {'dispatch_id': item.get('dispatch_id'), 'status': 'rejected', 'reason': item.get('reason')}
                for item in rejected
            ]
            await HTTP.actuator_tasks.ack(message_id, ack_items)
            inserted_count = len([item for item in accepted if item.get('queue_id')])
            if inserted_count:
                cls._last_task_received_time = time.time()
                cls._task_pull_interval = cls.ACTIVE_PULL_INTERVAL
            else:
                log.warning('HTTP拉取UI任务本轮没有新增入队，停止本轮拉取')
            return True
        except Exception as error:
            await ActuatorSystemErrorReporter.report(error, 'services/ui/case_flow:pull_case_task_by_http')
            if cls._is_http_pull_not_found(error):
                cls._http_pull_disabled = True
                log.warning('HTTP拉取UI任务接口不存在，本次执行器进程将直接回退WebSocket拉取任务')
            else:
                TaskPullFailureReporter.report('UI', error)
            return False

    @classmethod
    async def get_case_task_by_websocket(cls):
        try:
            if settings.IS_OPEN:
                from src.network import ActuatorToolsEventEnum, socket_conn
                from src.tools.set_config import SetConfig
                await socket_conn.async_send(
                    '请求获取任务',
                    func_name=ActuatorToolsEventEnum.GET_TASK.value,
                    func_args=TaskPullRequest(type=TestCaseTypeEnum.UI, username=SetConfig.get_username())
                )
        except Exception as error:
            await ActuatorSystemErrorReporter.report(error, 'services/ui/case_flow:get_case_task_by_websocket')
            log.error(f'get_case_task失败，类型：{type(error)}，失败详情：{error}，失败明细：{traceback.format_exc()}')

    @classmethod
    @async_memory
    async def execute_task(cls, queue_id: int, case_model: CaseModel):
        save_ui_debug_payload(case_model, '用例')
        activity_id = execution_identity(case_model, "ui-case")
        ExecutionActivity.start(
            activity_id, "UI 用例", case_model.name, case_model.send_user,
            progress_total=len(case_model.steps),
        )
        success = False
        error_message = ""
        try:
            async with TestCase(cls.parent, case_model, cls.get_web_runtime()) as obj:
                send_global_msg(f'开始执行UI测试用例：{case_model.name}', log_level='info')
                await obj.case_main()
                success = bool(obj.case_result.status)
                error_message = obj.case_result.error_message or ""
        except Exception as error:
            await ActuatorSystemErrorReporter.report(error, 'services/ui/case_flow:execute_task')
            error_message = str(error)
            ExecutionCaseQueue.mark_error(queue_id, error)
            log.error(f'执行UI测试用例任务异常，类型：{type(error)}，失败详情：{error}，失败明细：{traceback.format_exc()}')
        finally:
            ExecutionActivity.finish(activity_id, success, error_message)
            cls._running_task_handles.pop(queue_id, None)
            ExecutionCaseQueue.delete(queue_id)
            cls.running_tasks = max(0, cls.running_tasks - 1)

    @classmethod
    async def add_task(cls, case_model: CaseModel):
        try:
            queue_id = ExecutionCaseQueue.insert(
                ExecutionCaseQueue.TYPE_UI,
                json_dumps(case_model),
            )
            cls._last_task_received_time = time.time()
            cls._task_pull_interval = cls.ACTIVE_PULL_INTERVAL
            log.info(f'UI测试用例已写入本地执行队列，queue_id={queue_id}，case_id={case_model.id}')
        except ExecutionCaseQueueFull as error:
            msg = f'UI本地执行队列已满，任务【{case_model.name}】未入队，请稍后重试'
            log.warning(f'{msg}，详情：{error}')
            send_global_msg(msg)
            await socket_conn.async_send(
                msg=msg,
                code=300,
                is_notice=ClientTypeEnum.WEB,
                user=case_model.send_user,
            )

    @classmethod
    async def execute_direct(cls, case_model: CaseModel):
        """执行统一任务表领取的单个 UI Case，并将最终结果交还任务工作器。"""
        activity_id = execution_identity(case_model, "ui-case-task")
        ExecutionActivity.start(
            activity_id, "UI 用例", case_model.name, case_model.send_user,
            progress_total=len(case_model.steps),
        )
        async with TestCase(cls.parent, case_model, cls.get_web_runtime()) as obj:
            try:
                send_global_msg(f'开始执行UI测试用例：{case_model.name}', log_level='info')
                await obj.case_main()
                return obj.case_result
            finally:
                ExecutionActivity.finish(
                    activity_id,
                    bool(obj.case_result.status),
                    obj.case_result.error_message or '',
                )

    @classmethod
    def stop(cls):
        cls.running = False

    @classmethod
    async def cancel_test_suite(cls, test_suite_id: int) -> dict:
        removed_pending = ExecutionCaseQueue.remove_pending_by_test_suite(
            test_suite_id,
            ExecutionCaseQueue.TYPE_UI,
        )
        running_tasks = [
            task
            for suite_id, task in list(cls._running_task_handles.values())
            if suite_id == int(test_suite_id) and not task.done()
        ]
        for task in running_tasks:
            task.cancel()
        if running_tasks:
            await asyncio.gather(*running_tasks, return_exceptions=True)
        return {
            'removed_pending': removed_pending,
            'cancelled_running': len(running_tasks),
        }

    @classmethod
    def wake_pull(cls):
        cls._last_task_pull_time = 0.0
        cls._task_pull_interval = 0
        cls._force_pull = True

    @classmethod
    def recover_queue(cls):
        if cls._queue_recovered:
            return
        ExecutionCaseQueue.recover_running()
        cls._queue_recovered = True

    @classmethod
    def reset_web_runtime(cls):
        cls.web_runtime = AutomationSessionManager.reset_web_runtime()

    @classmethod
    def get_web_runtime(cls):
        if cls.web_runtime is None:
            cls.web_runtime = AutomationSessionManager.web_runtime()
        return cls.web_runtime

    @classmethod
    def refill_trigger(cls, queue_limit: int):
        try:
            parallel_size = max(1, int(SetConfig.get_web_parallel() or 5))  # type: ignore
        except (TypeError, ValueError):
            parallel_size = 5
        except Exception as _unexpected_error:
            ActuatorSystemErrorReporter.schedule(_unexpected_error, 'services/ui/case_flow:refill_trigger')
            parallel_size = 5
        return max(parallel_size, int(queue_limit * 0.5))

    @staticmethod
    def _is_http_pull_not_found(error: Exception):
        error_text = str(error)
        return '404' in error_text or 'Not Found' in error_text
