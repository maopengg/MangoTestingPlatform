import socket
import threading
from datetime import datetime, timedelta

from apscheduler.triggers.cron import CronTrigger
from django.utils import timezone
from mangotools.enums import StatusEnum

from src.apps.system.enums import RuntimeServiceName
from src.apps.system.services.runtime_center.heartbeat import ServiceHeartbeatService
from src.apps.system.services.runtime_center.system_error_event import SystemErrorEventSource
from src.apps.task_center.enums import ScheduleFireSourceTypeEnum
from src.apps.task_center.selectors.querysets import TaskCenterQuerySelector
from src.apps.task_center.services.scheduling.consumer import ScheduleFireConsumer
from src.apps.task_center.services.scheduling.fire import ScheduleFireService
from src.apps.task_center.services.scheduling.task_group_execution import (
    ScheduledTaskGroupExecutionService,
)
from src.common.decorators.retry import async_task_db_connection
from src.common.decorators.system_error import system_error_guard
from src.common.logging import log
from src.processes.scheduler.system_jobs import SchedulerSystemJobService


class ScheduleRunner:
    def __init__(
            self,
            node_name: str | None = None,
            poll_interval: int = 30,
            lookback_minutes: int = 1,
            dispatch_batch_size: int = 50,
    ):
        self.node_name = node_name or socket.gethostname()
        self.poll_interval = poll_interval
        self.lookback_minutes = lookback_minutes
        self.dispatch_batch_size = dispatch_batch_size
        self.running = True
        self.stop_event = threading.Event()
        self.dispatch_wakeup_event = threading.Event()
        self.dispatch_consumer = ScheduleFireConsumer(
            self.node_name,
            self.stop_event,
            self.dispatch_wakeup_event,
        )
        self.dispatch_consumer_thread = None

    @system_error_guard(
        source=SystemErrorEventSource.SCHEDULER,
        request_path='run_scheduler',
        service_name=RuntimeServiceName.SCHEDULER,
    )
    def run_forever(self):
        log.system.info(f'scheduler-service 启动：node={self.node_name}，已合并定时触发和任务分发')
        self.start_dispatch_consumer()
        try:
            while self.running and not self.stop_event.is_set():
                self.ensure_dispatch_consumer()
                ServiceHeartbeatService.beat_if_due(
                    self,
                    RuntimeServiceName.SCHEDULER,
                    instance_name=self.node_name,
                    metadata={
                        'dispatch_batch_size': self.dispatch_batch_size,
                        'poll_interval': self.poll_interval,
                        'lookback_minutes': self.lookback_minutes,
                        'dispatch_consumer_alive': self.is_dispatch_consumer_alive(),
                    },
                )
                self.tick()
                self.stop_event.wait(self.poll_interval)
        finally:
            self.stop()

    def start_dispatch_consumer(self):
        if self.is_dispatch_consumer_alive() or self.stop_event.is_set():
            return
        self.dispatch_consumer_thread = threading.Thread(
            target=self.dispatch_consumer.run_forever,
            name=f'mango-schedule-fire-consumer-{self.node_name}',
            daemon=True,
        )
        self.dispatch_consumer_thread.start()

    def ensure_dispatch_consumer(self):
        if not self.is_dispatch_consumer_alive():
            log.system.warning(
                f'scheduler-service 触发记录消费者未运行，正在重新启动：node={self.node_name}'
            )
            self.start_dispatch_consumer()

    def is_dispatch_consumer_alive(self) -> bool:
        return bool(self.dispatch_consumer_thread and self.dispatch_consumer_thread.is_alive())

    def stop(self):
        self.running = False
        self.stop_event.set()
        self.dispatch_wakeup_event.set()
        if (
                self.dispatch_consumer_thread
                and self.dispatch_consumer_thread.is_alive()
                and self.dispatch_consumer_thread is not threading.current_thread()
        ):
            self.dispatch_consumer_thread.join(timeout=10)

    @async_task_db_connection(max_retries=1, retry_delay=1)
    def tick(self):
        now = timezone.now().replace(second=0, microsecond=0)
        for offset in range(self.lookback_minutes):
            planned_at = now - timedelta(minutes=offset)
            self.create_due_time_task_fires(planned_at)
            self.run_due_system_jobs(planned_at)
        self.dispatch_wakeup_event.set()

    def create_due_time_task_fires(self, planned_at: datetime):
        time_tasks = TaskCenterQuerySelector.time_tasks().filter(cron__isnull=False)
        for time_task in time_tasks:
            if not time_task.cron or not self.is_due(time_task.cron, planned_at):
                continue
            if self.has_api_auth_to_refresh(time_task.id) or self.has_ui_auth_to_refresh(time_task.id):
                token_fire, token_created = ScheduleFireService.create_token_refresh_fire(
                    time_task=time_task,
                    planned_at=planned_at,
                    node_name=self.node_name,
                )
                if token_created:
                    try:
                        api_refresh_count = self.refresh_api_auth(time_task.id)
                        ui_refresh_count = self.refresh_ui_auth(time_task.id)
                        ScheduleFireService.mark_success(
                            token_fire.id,
                            self.node_name,
                            extra_data={
                                'refresh_count': api_refresh_count + ui_refresh_count,
                                'api_refresh_count': api_refresh_count,
                                'ui_refresh_count': ui_refresh_count,
                            },
                        )
                    except Exception as error:
                        ScheduleFireService.mark_failed(token_fire.id, str(error), self.node_name)
            tasks = list(TaskCenterQuerySelector.tasks().filter(
                status=StatusEnum.SUCCESS.value,
                timing_strategies=time_task.id,
            ).select_related('task_group').distinct())
            grouped_tasks = {}
            standalone_tasks = []
            for task in tasks:
                if task.task_group_id:
                    grouped_tasks.setdefault(task.task_group_id, []).append(task)
                else:
                    standalone_tasks.append(task)

            for task in standalone_tasks:
                for test_env in task.test_envs or []:
                    ScheduleFireService.create_test_suite_fire(
                        task,
                        time_task,
                        test_env,
                        planned_at,
                        self.node_name,
                    )

            for group_tasks in grouped_tasks.values():
                group = group_tasks[0].task_group
                for test_env in group.test_envs or []:
                    execution, _fires = ScheduledTaskGroupExecutionService.prepare(
                        group,
                        time_task,
                        group_tasks,
                        test_env,
                        planned_at,
                        node_name=self.node_name,
                    )
                    # prepare 可能命中已存在的触发记录；无论是否新建，都检查一次
                    # 批次完成状态，避免生成失败的任务组长期等待。
                    ScheduledTaskGroupExecutionService.try_finalize(execution.id)

    def run_due_system_jobs(self, planned_at: datetime):
        # 页面展示与调度执行必须共用同一份任务定义，避免新增任务只展示但从未触发。
        from src.apps.task_center.services.scheduling.system_job import SystemJobService

        jobs = [
            (
                job.key,
                job.cron,
                ScheduleFireService.create_data_cleanup_fire
                if job.source_type == ScheduleFireSourceTypeEnum.DATA_CLEANUP.value
                else ScheduleFireService.create_system_job_fire,
                job.handler,
            )
            for job in SystemJobService.JOBS
        ]
        # 性能任务恢复尚未纳入管理页面，保留原有后台任务行为。
        jobs.append((
            'recover_perf_runs',
            '* * * * *',
            ScheduleFireService.create_system_job_fire,
            SchedulerSystemJobService.recover_perf_runs,
        ))
        for job_name, cron, fire_creator, handler in jobs:
            if not self.is_due(cron, planned_at):
                continue
            fire, created = fire_creator(job_name=job_name, planned_at=planned_at, node_name=self.node_name)
            if not created:
                continue
            try:
                handler_kwargs = (
                    {'schedule_fire_id': fire.id}
                    if job_name == 'scan_data_factory_entity_field_updates'
                    else {}
                )
                result = handler(**handler_kwargs)
                ScheduleFireService.mark_success(
                    fire.id,
                    self.node_name,
                    extra_data=result if isinstance(result, dict) else None,
                )
            except Exception as error:
                ScheduleFireService.mark_failed(fire.id, str(error), self.node_name)

    @staticmethod
    def refresh_api_auth(timing_strategy_id: int):
        try:
            from src.apps.auto_api.services.base.api_base_test_setup.auth_manager import ApiAuthManager
            return ApiAuthManager.refresh_by_time_task(timing_strategy_id)
        except Exception as error:
            log.system.error(
                f'scheduler-service 执行 API 授权 Token 定时刷新异常：time_task={timing_strategy_id}, error={error}')
            raise

    @staticmethod
    def has_api_auth_to_refresh(timing_strategy_id: int) -> bool:
        from src.apps.auto_api.services.base.api_base_test_setup.auth_manager import ApiAuthManager
        return ApiAuthManager.has_timing_refresh_config(timing_strategy_id)

    @staticmethod
    def refresh_ui_auth(timing_strategy_id: int):
        try:
            from src.apps.auto_ui.services.ui_auth import UiAuthManager
            return UiAuthManager.refresh_by_time_task(timing_strategy_id)
        except Exception as error:
            log.system.error(
                f'scheduler-service 执行 UI 授权定时刷新异常：time_task={timing_strategy_id}, error={error}')
            raise

    @staticmethod
    def has_ui_auth_to_refresh(timing_strategy_id: int) -> bool:
        from src.apps.auto_ui.services.ui_auth import UiAuthManager
        return UiAuthManager.has_timing_refresh_config(timing_strategy_id)

    @staticmethod
    def is_due(cron: str, planned_at: datetime) -> bool:
        try:
            trigger = CronTrigger.from_crontab(cron)
            previous = planned_at - timedelta(seconds=1)
            next_fire = trigger.get_next_fire_time(None, previous)
            if next_fire is None:
                return False
            return next_fire.replace(tzinfo=None, second=0, microsecond=0) == planned_at.replace(tzinfo=None)
        except Exception as error:
            log.system.error(f'解析定时策略 cron 失败：cron={cron}, error={error}')
            return False
