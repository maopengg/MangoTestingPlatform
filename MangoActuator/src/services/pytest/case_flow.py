# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2025-08-27 10:19
# @Author : 毛鹏

import asyncio
import json
import time
import traceback
import uuid

from mangotools.enums import ClientTypeEnum
from mangotools.enums import StatusEnum
from mangotools.contracts import PytestExecutionCommand
from src.network import socket_conn
from src.services.pytest.test_case import TestCase
from src.services.task_pull_failure import TaskPullFailureReporter
from src.settings import settings
from src.storage.sqlite import ExecutionCaseQueue, ExecutionCaseQueueFull
from src.tools.json_tools import json_dumps
from src.tools.log_collector import log
from src.tools.send_global_msg import send_global_msg
from src.tools.execution_activity import ExecutionActivity, execution_identity


class PytestCaseFlow:
    ACTIVE_PULL_INTERVAL = 5
    EMPTY_PULL_INTERVAL = 10
    running_tasks = 0
    parent = None
    running = True
    _queue_recovered = False
    _last_task_pull_time = 0.0
    _last_task_received_time = 0.0
    _task_pull_interval = ACTIVE_PULL_INTERVAL
    _force_pull = False
    _running_task_handles: dict[int, tuple[int | None, asyncio.Task]] = {}

    @classmethod
    async def process_tasks(cls):
        cls.recover_queue()
        while cls.running:
            try:
                await asyncio.sleep(0.1)
                if cls.running_tasks < cls.parallel_limit() and ExecutionCaseQueue.pending_count(ExecutionCaseQueue.TYPE_PYTEST):
                    queue_item = ExecutionCaseQueue.fetch_next(ExecutionCaseQueue.TYPE_PYTEST)
                    if not queue_item:
                        continue
                    try:
                        case_model = PytestExecutionCommand(**json.loads(queue_item['payload']))
                    except Exception as error:
                        ExecutionCaseQueue.mark_error(queue_item['id'], error)
                        ExecutionCaseQueue.delete(queue_item['id'])
                        log.error(
                            f'Pytest本地执行队列任务反序列化失败，已删除，queue_id={queue_item["id"]}，'
                            f'失败详情：{error}，失败明细：{traceback.format_exc()}'
                        )
                        continue
                    cls.running_tasks += 1
                    task = asyncio.create_task(cls.execute_task(queue_item['id'], case_model))
                    cls._running_task_handles[queue_item['id']] = (case_model.test_suite_id, task)
                await cls.maybe_get_case_task()
            except asyncio.CancelledError:
                raise
            except Exception as error:
                log.error(
                    f'Pytest用例调度循环异常，调度器继续运行，类型：{type(error)}，'
                    f'失败详情：{error}，失败明细：{traceback.format_exc()}'
                )
                await asyncio.sleep(1)

    @classmethod
    async def maybe_get_case_task(cls):
        from src.services.capabilities import CapabilityRegistry

        if not CapabilityRegistry.ready("pytest"):
            return
        if not settings.IS_OPEN:
            return
        queue_count = ExecutionCaseQueue.count(ExecutionCaseQueue.TYPE_PYTEST)
        queue_limit = ExecutionCaseQueue.queue_limit(ExecutionCaseQueue.TYPE_PYTEST)
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
        await cls.pull_case_task_by_http()

    @classmethod
    async def pull_case_task_by_http(cls) -> bool:
        try:
            from src.network import HTTP
            queue_limit = ExecutionCaseQueue.queue_limit(ExecutionCaseQueue.TYPE_PYTEST)
            queue_count = ExecutionCaseQueue.count(ExecutionCaseQueue.TYPE_PYTEST)
            capacity = queue_limit - queue_count
            if capacity <= 0:
                return True
            batch_size = min(5, capacity)
            message_id = str(uuid.uuid4())
            resp = await HTTP.actuator_tasks.pull(
                message_id=message_id,
                task_type=ExecutionCaseQueue.TYPE_PYTEST,
                capacity=batch_size,
                local_queue_size=queue_count,
                max_queue_size=queue_limit,
            )
            TaskPullFailureReporter.recovered('Pytest')
            if resp.get('code') != 200:
                return False
            data = resp.get('data') if isinstance(resp, dict) else {}
            tasks = data.get('tasks') if isinstance(data, dict) else []
            if not tasks:
                return True
            accepted, rejected = ExecutionCaseQueue.bulk_insert(
                ExecutionCaseQueue.TYPE_PYTEST,
                tasks,
                source_message_id=message_id,
            )
            if rejected:
                msg = f'Pytest本地执行队列拒绝入队 {len(rejected)} 条任务，请检查队列容量配置'
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
                log.warning('HTTP拉取Pytest任务本轮没有新增入队，停止本轮拉取')
            return True
        except Exception as error:
            TaskPullFailureReporter.report('Pytest', error)
            return False

    @classmethod
    async def execute_task(cls, queue_id: int, case_model: PytestExecutionCommand):
        activity_id = execution_identity(case_model, "pytest-case")
        ExecutionActivity.start(activity_id, "Pytest 用例", case_model.name, case_model.send_user, progress_total=1)
        success = False
        error_message = ""
        case_runner = TestCase(cls.parent, case_model)
        try:
            async with case_runner as obj:
                send_global_msg(f'开始执行Pytest用例：{case_model.name}')
                await obj.test_case()
                success = bool(obj.case_result.status)
                ExecutionActivity.update(activity_id, progress_current=1)
        except Exception as error:
            error_message = str(error)
            ExecutionCaseQueue.mark_error(queue_id, error)
            log.error(f'执行Pytest用例任务异常，类型：{type(error)}，失败详情：{error}，失败明细：{traceback.format_exc()}')
            case_runner.case_result.status = StatusEnum.FAIL.value
            case_runner.case_result.result_data = [{
                'name': case_model.name,
                'status': StatusEnum.FAIL.value,
                'statusDetails': {'message': error_message or type(error).__name__},
            }]
            try:
                await case_runner.send_case_result()
            except Exception as report_error:
                log.error(f'Pytest异常结果回传失败：case_id={case_model.id}，详情：{report_error}')
        finally:
            ExecutionActivity.finish(activity_id, success, error_message)
            cls._running_task_handles.pop(queue_id, None)
            ExecutionCaseQueue.delete(queue_id)
            cls.running_tasks = max(0, cls.running_tasks - 1)

    @classmethod
    async def add_task(cls, case_model: PytestExecutionCommand):
        try:
            queue_id = ExecutionCaseQueue.insert(
                ExecutionCaseQueue.TYPE_PYTEST,
                json_dumps(case_model),
            )
            cls._last_task_received_time = time.time()
            cls._task_pull_interval = cls.ACTIVE_PULL_INTERVAL
            log.info(f'Pytest用例已写入本地执行队列，queue_id={queue_id}，case_id={case_model.id}')
        except ExecutionCaseQueueFull as error:
            msg = f'Pytest本地执行队列已满，任务【{case_model.name}】未入队，请稍后重试'
            log.warning(f'{msg}，详情：{error}')
            send_global_msg(msg)
            await socket_conn.async_send(
                msg=msg,
                code=300,
                is_notice=ClientTypeEnum.WEB,
                user=case_model.send_user,
            )

    @classmethod
    def stop(cls):
        cls.running = False

    @classmethod
    async def cancel_test_suite(cls, test_suite_id: int) -> dict:
        removed_pending = ExecutionCaseQueue.remove_pending_by_test_suite(
            test_suite_id,
            ExecutionCaseQueue.TYPE_PYTEST,
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
    def parallel_limit(cls):
        try:
            from src.tools.set_config import SetConfig
            return max(1, int(SetConfig.get_pytest_parallel() or 5))  # type: ignore
        except Exception as error:
            log.warning(f'读取Pytest并行数失败，使用默认值5，详情：{error}')
            return 5

    @classmethod
    def refill_trigger(cls, queue_limit: int):
        return max(cls.parallel_limit(), int(queue_limit * 0.5))
