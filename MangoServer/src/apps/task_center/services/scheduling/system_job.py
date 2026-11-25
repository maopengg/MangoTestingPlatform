import socket
from dataclasses import dataclass
from typing import Callable

from apscheduler.triggers.cron import CronTrigger
from django.utils import timezone

from src.apps.task_center.enums import ScheduleFireSourceTypeEnum
from src.apps.task_center.models import ScheduleFire
from src.apps.task_center.services.scheduling.fire import ScheduleFireService
from src.common.exceptions import MangoServerError
from src.processes.scheduler.system_jobs import SchedulerSystemJobService


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
            key='clean_runtime_kv',
            name='运行态键值过期清理',
            description='每 5 分钟分批清理独立 RuntimeKV 表中的过期数据，不处理现有配置或 Django 缓存。',
            cron='*/5 * * * *',
            source_type=ScheduleFireSourceTypeEnum.DATA_CLEANUP.value,
            handler=SchedulerSystemJobService.clean_runtime_kv,
        ),
        SystemJobDefinition(
            key='repair_test_suite_status',
            name='测试套卡住状态修复',
            description='每 10 分钟修复测试套完成状态，并重置或失败超时执行明细。',
            cron='*/10 * * * *',
            source_type=ScheduleFireSourceTypeEnum.SYSTEM_JOB.value,
            handler=SchedulerSystemJobService.repair_test_suite_status,
        ),
        SystemJobDefinition(
            key='recover_api_report_executions',
            name='API 报告执行自动恢复',
            description='每分钟最多检查 100 条新版恢复记录；恢复原结果和清理责任，安全后按原重试预算重新入队，并补偿失败的系统异常登记。',
            cron='* * * * *',
            source_type=ScheduleFireSourceTypeEnum.SYSTEM_JOB.value,
            handler=SchedulerSystemJobService.recover_api_report_executions,
        ),
        SystemJobDefinition(
            key='send_pending_test_suite_notice',
            name='测试报告通知补偿',
            description='每 3 分钟发送未发送的测试报告通知。',
            cron='*/3 * * * *',
            source_type=ScheduleFireSourceTypeEnum.SYSTEM_JOB.value,
            handler=SchedulerSystemJobService.send_pending_test_suite_notice,
        ),
        SystemJobDefinition(
            key='reconcile_auth_risk_todos',
            name='授权风险代办同步',
            description='每 3 分钟统一扫描 UI 与 API 授权风险，生成待办并向负责人及配置的通知组发送提醒。',
            cron='*/3 * * * *',
            source_type=ScheduleFireSourceTypeEnum.SYSTEM_JOB.value,
            handler=SchedulerSystemJobService.reconcile_auth_risk_todos,
        ),
        SystemJobDefinition(
            key='reconcile_workbench_todos',
            name='首页风险待办同步',
            description='每 5 分钟补偿数据工厂遗漏清理、同步非授权风险与 API Case 预发布审核待办，并自动关闭已恢复待办。',
            cron='*/5 * * * *',
            source_type=ScheduleFireSourceTypeEnum.SYSTEM_JOB.value,
            handler=SchedulerSystemJobService.reconcile_workbench_todos,
        ),
        SystemJobDefinition(
            key='reconcile_execution_statuses',
            name='执行状态一致性修复',
            description=(
                '每 10 分钟根据已结束的执行器任务，修复遗漏回写且没有更新执行任务的业务状态。'
            ),
            cron='*/10 * * * *',
            source_type=ScheduleFireSourceTypeEnum.SYSTEM_JOB.value,
            handler=SchedulerSystemJobService.reconcile_execution_statuses,
        ),
        SystemJobDefinition(
            key='clean_execution_result_data',
            name='执行结果完整数据清理',
            description='每天 00:10 按系统配置清理完整结果、排查文档、导出文件、性能抓包及UI执行产物；结果类默认60天，UI产物默认30天。',
            cron='10 0 * * *',
            source_type=ScheduleFireSourceTypeEnum.DATA_CLEANUP.value,
            handler=SchedulerSystemJobService.clean_execution_result_data,
        ),
        SystemJobDefinition(
            key='clean_data_factory_executions',
            name='数据工厂执行记录清理',
            description='每天 00:30 按配置删除已清理的数据工厂执行记录，默认保留 60 天；有清理时间时按清理时间计算，否则按创建时间计算。',
            cron='30 0 * * *',
            source_type=ScheduleFireSourceTypeEnum.DATA_CLEANUP.value,
            handler=SchedulerSystemJobService.clean_data_factory_executions,
        ),
        SystemJobDefinition(
            key='clean_sql_execution_records',
            name='SQL执行记录清理',
            description='每天 00:45 删除创建时间早于两个月的 SQL 执行记录。',
            cron='45 0 * * *',
            source_type=ScheduleFireSourceTypeEnum.DATA_CLEANUP.value,
            handler=SchedulerSystemJobService.clean_sql_execution_records,
        ),
        SystemJobDefinition(
            key='scan_data_factory_entity_field_updates',
            name='数据工厂字段更新扫描',
            description='每天 03:30 按数据库批量检测已绑定 MySQL 表结构，发现变化后停用对应数据实体。',
            cron='30 3 * * *',
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
        SystemJobDefinition(
            key='clean_api_case_execution_traces',
            name='API 用例执行链路清理',
            description='每小时 15 分有界分批清理超过保留期的已结束 trace/step；待核查及资源台账引用保留，未清完下轮续跑。',
            cron='15 * * * *',
            source_type=ScheduleFireSourceTypeEnum.DATA_CLEANUP.value,
            handler=SchedulerSystemJobService.clean_api_case_execution_traces,
        ),

        SystemJobDefinition(
            key='clean_mock_request_logs',
            name='Mock 调用记录清理',
            description='每天 02:40 分批删除超过 1 个月的 Mock 调用记录。',
            cron='40 2 * * *',
            source_type=ScheduleFireSourceTypeEnum.DATA_CLEANUP.value,
            handler=SchedulerSystemJobService.clean_mock_request_logs,
        ),
        SystemJobDefinition(
            key='cleanup_service_heartbeat',
            name='服务心跳清理',
            description='每天 02:30 删除超过 7 天的服务心跳记录。',
            cron='30 2 * * *',
            source_type=ScheduleFireSourceTypeEnum.DATA_CLEANUP.value,
            handler=SchedulerSystemJobService.cleanup_service_heartbeat,
        ),
        SystemJobDefinition(
            key='clean_ui_element_ai_history',
            name='UI 元素 AI 历史清理',
            description='每天 02:50 清理过期或超过单元素环境保留上限的自愈记录与基线快照。',
            cron='50 2 * * *',
            source_type=ScheduleFireSourceTypeEnum.DATA_CLEANUP.value,
            handler=SchedulerSystemJobService.clean_ui_element_ai_history,
        ),
        SystemJobDefinition(
            key='recover_executor_tasks',
            name='执行器任务租约恢复',
            description=(
                '每分钟分批恢复租约到期、调度超时、执行超时或已取消的执行器任务。'
            ),
            cron='* * * * *',
            source_type=ScheduleFireSourceTypeEnum.SYSTEM_JOB.value,
            handler=SchedulerSystemJobService.recover_executor_tasks,
        ),
        SystemJobDefinition(
            key='cleanup_realtime_data',
            name='执行器连接回收',
            description='每 5 分钟回收失联执行器连接，不执行任务恢复和历史数据删除。',
            cron='*/5 * * * *',
            source_type=ScheduleFireSourceTypeEnum.DATA_CLEANUP.value,
            handler=SchedulerSystemJobService.cleanup_realtime_data,
        ),
        SystemJobDefinition(
            key='clean_executor_task_history',
            name='执行器历史数据清理',
            description='每天凌晨 02:00-07:59 每 10 分钟分批清理超过 7 天的已结束执行器任务和历史连接。',
            cron='*/10 2-7 * * *',
            source_type=ScheduleFireSourceTypeEnum.DATA_CLEANUP.value,
            handler=SchedulerSystemJobService.clean_executor_task_history,
        ),
        SystemJobDefinition(
            key='clean_system_error_events',
            name='系统异常记录清理',
            description='每天 03:00 删除超过 30 天的系统异常记录。',
            cron='0 3 * * *',
            source_type=ScheduleFireSourceTypeEnum.DATA_CLEANUP.value,
            handler=SchedulerSystemJobService.clean_system_error_events,
        ),
    ]

    @classmethod
    def list_jobs(
        cls, page: int = 1, page_size: int = 20, filters: dict[str, str] | None = None,
    ) -> tuple[list[dict], int]:
        conditions = {
            key: str(value).strip().casefold()
            for key, value in (filters or {}).items()
            if key in ('key', 'name', 'description', 'cron') and value is not None and str(value).strip()
        }
        filtered_jobs = [
            job for job in cls.JOBS
            if all(value in getattr(job, key).casefold() for key, value in conditions.items())
        ]
        source_types = {
            value.strip() for value in (filters or {}).get('source_type__in', '').split(',')
            if value.strip()
        }
        if source_types:
            filtered_jobs = [job for job in filtered_jobs if str(job.source_type) in source_types]
        statuses = {
            value.strip() for value in (filters or {}).get('latest_status__in', '').split(',')
            if value.strip()
        }
        error_message = str((filters or {}).get('latest_error_message') or '').strip().casefold()
        latest_fire_map = None
        if statuses or error_message:
            # 最近状态属于每个任务的最新一次触发，必须先取最新记录再筛选、分页。
            latest_fire_map = cls.latest_fire_map(filtered_jobs)
            filtered_jobs = [
                job for job in filtered_jobs
                if (not statuses or str(latest_fire_map.get(job.key, {}).get('status', 'untriggered')) in statuses)
                and (not error_message or error_message in str(
                    latest_fire_map.get(job.key, {}).get('error_message') or ''
                ).casefold())
            ]
        total = len(filtered_jobs)
        start = (page - 1) * page_size
        jobs = filtered_jobs[start:start + page_size]
        if latest_fire_map is None:
            latest_fire_map = cls.latest_fire_map(jobs)
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
            for item in jobs
        ], total

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
            handler_kwargs = (
                {'schedule_fire_id': fire.id}
                if job.key == 'scan_data_factory_entity_field_updates'
                else {}
            )
            result = job.handler(**handler_kwargs)
            extra_data = {
                'trigger_mode': 'manual',
                'job_key': job.key,
            }
            if isinstance(result, dict):
                extra_data.update(result)
            ScheduleFireService.mark_success(fire.id, node_name, extra_data=extra_data)
        except MangoServerError as error:
            ScheduleFireService.mark_skipped(fire.id, str(error), node_name)
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
    def latest_fire_map(cls, jobs: list[SystemJobDefinition] | None = None) -> dict[str, dict]:
        result = {}
        for item in jobs if jobs is not None else cls.JOBS:
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
