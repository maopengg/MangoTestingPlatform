import socket
import time
from datetime import datetime, timedelta

from apscheduler.triggers.cron import CronTrigger
from django.utils import timezone

from src.apps.auto_system.models import Tasks, TimeTasks
from src.common.enums.tools_enum import StatusEnum
from src.apps.task_center.services.schedule_fire_service import ScheduleFireService
from src.common.tools.decorator.retry import async_task_db_connection
from src.common.tools.log_collector import log
from src.services.runtime.scheduler.system_jobs import SchedulerSystemJobService


class ScheduleRunner:
    def __init__(self, node_name: str | None = None, poll_interval: int = 30, lookback_minutes: int = 1):
        self.node_name = node_name or socket.gethostname()
        self.poll_interval = poll_interval
        self.lookback_minutes = lookback_minutes
        self.running = True

    def run_forever(self):
        log.system.info(f'scheduler-service 启动：node={self.node_name}')
        while self.running:
            self.tick()
            time.sleep(self.poll_interval)

    @async_task_db_connection(max_retries=1, retry_delay=1)
    def tick(self):
        now = timezone.now().replace(second=0, microsecond=0)
        for offset in range(self.lookback_minutes):
            planned_at = now - timedelta(minutes=offset)
            self.create_due_time_task_fires(planned_at)
            self.run_due_system_jobs(planned_at)

    def create_due_time_task_fires(self, planned_at: datetime):
        time_tasks = TimeTasks.objects.filter(cron__isnull=False)
        for time_task in time_tasks:
            if not time_task.cron or not self.is_due(time_task.cron, planned_at):
                continue
            token_fire, token_created = ScheduleFireService.create_token_refresh_fire(
                time_task=time_task,
                planned_at=planned_at,
                node_name=self.node_name,
            )
            if token_created:
                try:
                    self.refresh_api_auth(time_task.id)
                    ScheduleFireService.mark_success(token_fire.id, self.node_name)
                except Exception as error:
                    ScheduleFireService.mark_failed(token_fire.id, str(error), self.node_name)
            tasks = Tasks.objects.select_related('timing_strategy').filter(
                status=StatusEnum.SUCCESS.value,
                timing_strategy_id=time_task.id,
            )
            for task in tasks:
                ScheduleFireService.create_test_suite_fire(task, planned_at, self.node_name)

    def run_due_system_jobs(self, planned_at: datetime):
        jobs = [
            ('repair_test_suite_status', '*/10 * * * *', ScheduleFireService.create_system_job_fire, SchedulerSystemJobService.repair_test_suite_status),
            ('send_pending_test_suite_notice', '* * * * *', ScheduleFireService.create_system_job_fire, SchedulerSystemJobService.send_pending_test_suite_notice),
            ('repair_api_case_status', '*/5 * * * *', ScheduleFireService.create_system_job_fire, SchedulerSystemJobService.repair_api_case_status),
            ('repair_ui_case_status', '*/5 * * * *', ScheduleFireService.create_system_job_fire, SchedulerSystemJobService.repair_ui_case_status),
            ('repair_pytest_case_status', '*/5 * * * *', ScheduleFireService.create_system_job_fire, SchedulerSystemJobService.repair_pytest_case_status),
            ('scan_data_factory_entity_field_updates', '0 8 * * *', ScheduleFireService.create_system_job_fire, SchedulerSystemJobService.scan_data_factory_entity_field_updates),
            ('clean_test_suite_detail_result', '0 0 * * *', ScheduleFireService.create_data_cleanup_fire, SchedulerSystemJobService.clean_test_suite_detail_result),
            ('clean_data_factory_executions', '30 0 * * *', ScheduleFireService.create_data_cleanup_fire, SchedulerSystemJobService.clean_data_factory_executions),
            ('clean_user_logs', '0 1 * * *', ScheduleFireService.create_data_cleanup_fire, SchedulerSystemJobService.clean_user_logs),
            ('clean_schedule_fires', '30 1 * * *', ScheduleFireService.create_data_cleanup_fire, SchedulerSystemJobService.clean_schedule_fires),
            ('clean_monitoring_reports', '0 2 * * *', ScheduleFireService.create_data_cleanup_fire, SchedulerSystemJobService.clean_monitoring_reports),
        ]
        for job_name, cron, fire_creator, handler in jobs:
            if not self.is_due(cron, planned_at):
                continue
            fire, created = fire_creator(job_name=job_name, planned_at=planned_at, node_name=self.node_name)
            if not created:
                continue
            try:
                result = handler()
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
            from src.apps.auto_api.service.base.api_base_test_setup.auth_manager import ApiAuthManager
            ApiAuthManager.refresh_by_time_task(timing_strategy_id)
        except Exception as error:
            log.system.error(f'scheduler-service 执行 API 授权 Token 定时刷新异常：time_task={timing_strategy_id}, error={error}')
            raise

    @staticmethod
    def is_due(cron: str, planned_at: datetime) -> bool:
        try:
            trigger = CronTrigger.from_crontab(cron)
            previous = planned_at - timedelta(minutes=1)
            next_fire = trigger.get_next_fire_time(None, previous)
            if next_fire is None:
                return False
            return next_fire.replace(tzinfo=None, second=0, microsecond=0) == planned_at.replace(tzinfo=None)
        except Exception as error:
            log.system.error(f'解析定时策略 cron 失败：cron={cron}, error={error}')
            return False
