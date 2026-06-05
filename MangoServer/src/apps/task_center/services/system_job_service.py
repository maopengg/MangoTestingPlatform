import socket
from dataclasses import dataclass
from typing import Callable

from apscheduler.triggers.cron import CronTrigger
from django.utils import timezone

from src.apps.task_center.enums import ScheduleFireSourceTypeEnum
from src.apps.task_center.models import ScheduleFire
from src.apps.task_center.services.schedule_fire_service import ScheduleFireService
from src.services.runtime.scheduler.system_jobs import SchedulerSystemJobService


@dataclass(frozen=True)
class SystemJobDefinition:
    key: str
    name: str
    description: str
    cron: str
    source_type: int
    handler: Callable

    @property
    def source_type_name(self):
        return ScheduleFireSourceTypeEnum.get_value(self.source_type)


class SystemJobService:
    JOBS = [
        SystemJobDefinition(
            key='repair_test_suite_status',
            name='测试套卡住状态修复',
            description='每 10 分钟修复测试套完成状态，并重置或失败超时执行明细。',
            cron='*/10 * * * *',
            source_type=ScheduleFireSourceTypeEnum.SYSTEM_JOB.value,
            handler=SchedulerSystemJobService.repair_test_suite_status,
        ),
        SystemJobDefinition(
            key='send_pending_test_suite_notice',
            name='测试报告通知补偿',
            description='每分钟发送未发送的测试报告通知。',
            cron='* * * * *',
            source_type=ScheduleFireSourceTypeEnum.SYSTEM_JOB.value,
            handler=SchedulerSystemJobService.send_pending_test_suite_notice,
        ),
        SystemJobDefinition(
            key='repair_api_case_status',
            name='API 用例卡住状态修复',
            description='将进行中超过 5 分钟仍未更新的 API 用例状态重置为待开始。',
            cron='*/5 * * * *',
            source_type=ScheduleFireSourceTypeEnum.SYSTEM_JOB.value,
            handler=SchedulerSystemJobService.repair_api_case_status,
        ),
        SystemJobDefinition(
            key='repair_ui_case_status',
            name='UI 用例卡住状态修复',
            description='将进行中超过 10 分钟仍未更新的 UI 用例状态置为失败。',
            cron='*/5 * * * *',
            source_type=ScheduleFireSourceTypeEnum.SYSTEM_JOB.value,
            handler=SchedulerSystemJobService.repair_ui_case_status,
        ),
        SystemJobDefinition(
            key='repair_pytest_case_status',
            name='Pytest 用例卡住状态修复',
            description='将进行中超过 5 分钟仍未更新的 Pytest 用例状态重置为待开始。',
            cron='*/5 * * * *',
            source_type=ScheduleFireSourceTypeEnum.SYSTEM_JOB.value,
            handler=SchedulerSystemJobService.repair_pytest_case_status,
        ),
        SystemJobDefinition(
            key='clean_test_suite_detail_result',
            name='测试详情大结果清理',
            description='每天 00:00 删除超过 30 天的 test_suite_detail_result 数据。',
            cron='0 0 * * *',
            source_type=ScheduleFireSourceTypeEnum.DATA_CLEANUP.value,
            handler=SchedulerSystemJobService.clean_test_suite_detail_result,
        ),
        SystemJobDefinition(
            key='clean_data_factory_executions',
            name='数据工厂执行记录清理',
            description='每天 00:30 删除超过 3 个月且清理状态为已清理的数据工厂执行记录。',
            cron='30 0 * * *',
            source_type=ScheduleFireSourceTypeEnum.DATA_CLEANUP.value,
            handler=SchedulerSystemJobService.clean_data_factory_executions,
        ),
        SystemJobDefinition(
            key='scan_data_factory_entity_field_updates',
            name='数据工厂字段更新扫描',
            description='每天 08:00 扫描数据工厂-工厂实体中字段有更新的任务，当前扫描逻辑待实现。',
            cron='0 8 * * *',
            source_type=ScheduleFireSourceTypeEnum.SYSTEM_JOB.value,
            handler=SchedulerSystemJobService.scan_data_factory_entity_field_updates,
        ),
        SystemJobDefinition(
            key='clean_user_logs',
            name='操作日志清理',
            description='每天 01:00 删除超过 3 个月的操作日志。',
            cron='0 1 * * *',
            source_type=ScheduleFireSourceTypeEnum.DATA_CLEANUP.value,
            handler=SchedulerSystemJobService.clean_user_logs,
        ),
        SystemJobDefinition(
            key='clean_schedule_fires',
            name='定时任务触发记录清理',
            description='每天 01:30 删除超过 30 天的定时任务触发记录。',
            cron='30 1 * * *',
            source_type=ScheduleFireSourceTypeEnum.DATA_CLEANUP.value,
            handler=SchedulerSystemJobService.clean_schedule_fires,
        ),
        SystemJobDefinition(
            key='clean_monitoring_reports',
            name='预警监控报告清理',
            description='每天 02:00 删除超过 1 个月的脚本运行器-预警监控报告。',
            cron='0 2 * * *',
            source_type=ScheduleFireSourceTypeEnum.DATA_CLEANUP.value,
            handler=SchedulerSystemJobService.clean_monitoring_reports,
        ),
    ]

    @classmethod
    def list_jobs(cls) -> list[dict]:
        latest_fire_map = cls.latest_fire_map()
        return [
            {
                'key': item.key,
                'name': item.name,
                'description': item.description,
                'cron': item.cron,
                'next_fire_at': cls.next_fire_at(item.cron),
                'source_type': item.source_type,
                'source_type_name': item.source_type_name,
                'latest_fire': latest_fire_map.get(item.key),
            }
            for item in cls.JOBS
        ]

    @classmethod
    def trigger(cls, job_key: str, node_name: str | None = None) -> ScheduleFire | None:
        job = cls.get_job(job_key)
        if not job:
            return None
        node_name = node_name or socket.gethostname()
        fire = ScheduleFireService.create_manual_system_fire(
            source_type=job.source_type,
            job_name=job.key,
            task_name=job.name,
            planned_at=timezone.now().replace(microsecond=0),
            node_name=node_name,
        )
        try:
            result = job.handler()
            extra_data = {
                'trigger_mode': 'manual',
                'job_key': job.key,
            }
            if isinstance(result, dict):
                extra_data.update(result)
            ScheduleFireService.mark_success(fire.id, node_name, extra_data=extra_data)
        except Exception as error:
            ScheduleFireService.mark_failed(fire.id, str(error), node_name)
        return ScheduleFire.objects.filter(id=fire.id).first()

    @classmethod
    def get_job(cls, job_key: str) -> SystemJobDefinition | None:
        for item in cls.JOBS:
            if item.key == job_key:
                return item
        return None

    @classmethod
    def get_job_by_fire_task_name(cls, task_name: str | None) -> SystemJobDefinition | None:
        for item in cls.JOBS:
            if task_name in {item.key, item.name, item.description}:
                return item
        return None

    @classmethod
    def get_job_by_fire(cls, fire: ScheduleFire) -> SystemJobDefinition | None:
        extra_data = fire.extra_data if isinstance(fire.extra_data, dict) else {}
        job_key = extra_data.get('job_key')
        if job_key:
            job = cls.get_job(job_key)
            if job:
                return job
        return cls.get_job_by_fire_task_name(fire.task_name)

    @classmethod
    def next_fire_at(cls, cron: str) -> str | None:
        try:
            now = timezone.now()
            next_fire = CronTrigger.from_crontab(cron).get_next_fire_time(None, now)
            if not next_fire:
                return None
            return timezone.localtime(next_fire).strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            return None

    @classmethod
    def latest_fire_map(cls) -> dict[str, dict]:
        result = {}
        for item in cls.JOBS:
            fire = ScheduleFire.objects.filter(
                source_type=item.source_type,
                task_name__in=[item.key, item.name],
            ).order_by('-planned_at', '-id').first()
            if not fire:
                continue
            result[item.key] = {
                'id': fire.id,
                'planned_at': fire.planned_at.strftime('%Y-%m-%d %H:%M:%S') if fire.planned_at else None,
                'fired_at': fire.fired_at.strftime('%Y-%m-%d %H:%M:%S') if fire.fired_at else None,
                'status': fire.status,
                'status_name': fire.get_status_display(),
                'error_message': fire.error_message,
                'extra_data': fire.extra_data,
            }
        return result
