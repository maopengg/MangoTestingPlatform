from datetime import timedelta
from uuid import uuid4

from django.db import transaction
from django.utils import timezone
from mangotools.enums import StatusEnum
from mangotools.enums import TaskEnum

from src.apps.system.enums import TestSuiteNoticeEnum
from src.apps.task_center.enums import ScheduleFireStatusEnum
from src.apps.task_center.exceptions import (
    SYSTEM_TASK_GROUP_TASK_NOT_FOUND,
    SYSTEM_TASK_GROUP_TASK_CONFIG_INVALID,
    TaskCenterError,
)
from src.apps.task_center.models import ScheduleFire, ScheduledTaskGroupExecution
from src.apps.task_center.models import ScheduledTaskGroup, Tasks, TimeTasks
from src.apps.task_center.services.scheduling.fire import ScheduleFireService
from src.apps.task_center.services.scheduling.task_group_notice import (
    TaskGroupChildReport,
    TaskGroupNoticeReport,
)
from src.apps.task_center.services.selection.case_selection import ScheduledTaskCaseSelectionService
from src.apps.test_center.enums.environment import EnvironmentEnum
from src.apps.test_center.models import TestSuite, TestSuiteDetails
from src.apps.test_center.services.reporting.test_suite.base_notice import NoticeMain
from src.apps.test_center.services.reporting.test_suite.summary import TestSuiteSummaryService
from src.apps.task_center.enums.execution import ReportRetentionPolicyEnum
from src.common.logging import log


class ScheduledTaskGroupExecutionService:
    @staticmethod
    def offline_report_product_id(execution_id):
        product_id = ScheduledTaskGroupExecution.objects.filter(id=execution_id).values_list('project_product_id', flat=True).first()
        if not product_id:
            raise TaskCenterError(SYSTEM_TASK_GROUP_TASK_NOT_FOUND)
        return product_id

    @classmethod
    def offline_report_source(cls, execution_id):
        execution = ScheduledTaskGroupExecution.objects.select_related('project_product__project').filter(id=execution_id).first()
        if not execution:
            raise TaskCenterError(SYSTEM_TASK_GROUP_TASK_NOT_FOUND)
        fires = list(ScheduleFire.objects.filter(group_execution_id=execution_id).select_related('test_suite', 'task').order_by('id'))
        if not fires or any(not cls._fire_completed(fire) for fire in fires):
            raise TaskCenterError(SYSTEM_TASK_GROUP_TASK_CONFIG_INVALID)
        return execution.project_product_id, cls._build_report(execution, fires)

    TERMINAL_SUITE_STATUSES = {
        TaskEnum.FAIL.value,
        TaskEnum.SUCCESS.value,
        TaskEnum.WARNING.value,
        TaskEnum.STOPPED.value,
        TaskEnum.INFRASTRUCTURE_BLOCKED.value,
    }
    TERMINAL_FIRE_STATUSES = {
        ScheduleFireStatusEnum.FAIL.value,
        ScheduleFireStatusEnum.SKIPPED.value,
        ScheduleFireStatusEnum.CANCELLED.value,
    }

    @staticmethod
    def execution_key(group_id: int, time_task_id: int, test_env: int, planned_at) -> str:
        return (
            f'group:{group_id}:time:{time_task_id}:environment:{test_env}:'
            f'{planned_at.strftime("%Y%m%d%H%M")}'
        )

    @classmethod
    @transaction.atomic
    def prepare(
            cls,
            group: ScheduledTaskGroup,
            time_task: TimeTasks | None,
            tasks: list[Tasks],
            test_env: int,
            planned_at,
            node_name: str | None = None,
            execution_key: str | None = None,
    ) -> tuple[ScheduledTaskGroupExecution, list[ScheduleFire]]:
        execution, execution_created = ScheduledTaskGroupExecution.objects.get_or_create(
            execution_key=execution_key or cls.execution_key(group.id, time_task.id, test_env, planned_at),
            defaults={
                'task_group': group,
                'task_group_name': group.name,
                'project_product_id': group.project_product_id,
                'time_task': time_task,
                'test_env': test_env,
                'planned_at': planned_at,
                'expected_count': len(tasks),
                'status': TaskEnum.PROCEED.value,
                'is_notice': group.is_notice,
                'notice_group_id': group.notice_group_id,
                'fail_notice': group.fail_notice,
            },
        )
        created_fires = []
        for task in tasks:
            fire, created = ScheduleFireService.create_test_suite_fire(
                task,
                time_task,
                test_env,
                planned_at,
                node_name=node_name,
                group_execution=execution,
            )
            if created and fire is not None:
                created_fires.append(fire)
        expected_count = ScheduleFire.objects.filter(group_execution=execution).count()
        if expected_count == 0:
            # 同一任务的多个策略在同一分钟命中时，其他批次已经占用了触发唯一键。
            # 本次新建的批次没有任何触发记录，不应保留成“进行中”的空批次。
            cls._discard_empty_execution(execution, execution_created)
            return execution, created_fires
        if execution.expected_count != expected_count:
            execution.expected_count = expected_count
            execution.save(update_fields=['expected_count', 'update_time'])
        return execution, created_fires

    @staticmethod
    def _discard_empty_execution(execution, execution_created: bool) -> bool:
        if not execution_created:
            return False
        log.system.warning(
            f'任务组批次未生成触发记录，已丢弃：execution={execution.id}, '
            f'group={execution.task_group_id}, environment={execution.test_env}',
        )
        execution.delete()
        return True

    @classmethod
    def trigger_manual(cls, group_id: int) -> dict:
        from src.apps.task_center.services.scheduling.dispatch import ScheduleDispatchService

        group = ScheduledTaskGroup.objects.filter(id=group_id, archived=False).first()
        if group is None:
            raise TaskCenterError(SYSTEM_TASK_GROUP_TASK_NOT_FOUND)
        # 手动触发与单任务一致，不受定时开关限制，也不重复执行每个定时策略。
        tasks = list(Tasks.objects.filter(task_group=group).order_by('id'))
        if not tasks:
            raise TaskCenterError(SYSTEM_TASK_GROUP_TASK_CONFIG_INVALID, value=('任务组没有可触发的子任务',))
        environments = ScheduledTaskCaseSelectionService.normalize_test_envs(group.test_envs)
        planned_at = timezone.now()
        trigger_key = uuid4().hex
        batches = []
        generated_count = 0
        failed_count = 0
        for test_env in environments:
            execution, fires = cls.prepare(
                group, None, tasks, test_env, planned_at,
                execution_key=f'manual:group:{group.id}:environment:{test_env}:{trigger_key}',
            )
            for fire in fires:
                if ScheduleDispatchService.dispatch_fire(fire) is not None:
                    generated_count += 1
                else:
                    failed_count += 1
            batches.append(execution.id)
        for execution_id in batches:
            cls.try_finalize(execution_id)
        return {
            'task_count': len(tasks),
            'execution_count': len(batches),
            'generated_count': generated_count,
            'failed_count': failed_count,
        }

    @classmethod
    def complete_test_suite(cls, test_suite_id: int) -> bool:
        fire = ScheduleFire.objects.filter(
            test_suite_id=test_suite_id,
            group_execution__isnull=False,
        ).only('id', 'group_execution_id').first()
        if fire is None:
            return False
        suite_status = TestSuite.objects.filter(id=test_suite_id).values_list('status', flat=True).first()
        if suite_status not in cls.TERMINAL_SUITE_STATUSES:
            return True
        now = timezone.now()
        TestSuite.objects.filter(id=test_suite_id).update(
            is_notice=TestSuiteNoticeEnum.EXPIRED.value,
        )
        fire_status = (
            ScheduleFireStatusEnum.FAIL.value
            if suite_status in (TaskEnum.FAIL.value, TaskEnum.STOPPED.value)
            else ScheduleFireStatusEnum.SUCCESS.value
        )
        ScheduleFire.objects.filter(id=fire.id).update(
            status=fire_status,
            update_time=now,
        )
        cls.try_finalize(fire.group_execution_id)
        return True

    @classmethod
    def try_finalize(cls, execution_id: int) -> bool:
        payload = cls._claim_notice(execution_id)
        if payload is None:
            cls._cleanup_finished_reports(execution_id)
            return False
        try:
            NoticeMain(payload['notice_group_id']).notice_task_group(payload['report'])
        except Exception:
            ScheduledTaskGroupExecution.objects.filter(
                id=execution_id,
                notice_status=TestSuiteNoticeEnum.SENDING.value,
            ).update(
                notice_status=TestSuiteNoticeEnum.NOT_SENT.value,
                update_time=timezone.now(),
            )
            raise
        ScheduledTaskGroupExecution.objects.filter(
            id=execution_id,
            notice_status=TestSuiteNoticeEnum.SENDING.value,
        ).update(
            notice_status=TestSuiteNoticeEnum.SENT.value,
            update_time=timezone.now(),
        )
        cls._cleanup_finished_reports(execution_id)
        return True

    @classmethod
    def _cleanup_finished_reports(cls, execution_id):
        from src.apps.test_center.services.reporting.test_suite.retention import TestSuiteRetentionService
        try:
            suite_ids = list(ScheduleFire.objects.filter(
                group_execution_id=execution_id,
                group_execution__status__in=cls.TERMINAL_SUITE_STATUSES,
                group_execution__notice_status__in=(TestSuiteNoticeEnum.SENT.value, TestSuiteNoticeEnum.EXPIRED.value),
                test_suite__report_retention_policy=ReportRetentionPolicyEnum.ABNORMAL_ONLY.value,
                test_suite__report_retained=True,
                test_suite__status=TaskEnum.SUCCESS.value,
            ).values_list('test_suite_id', flat=True))
        except Exception:
            log.system.exception(f'任务组报告清理查询失败，保留原报告：execution={execution_id}')
            return
        for suite_id in suite_ids:
            TestSuiteRetentionService.cleanup_safely(suite_id)

    @classmethod
    def resend_notice(cls, group_id: int, execution_id: int) -> None:
        payload = cls._claim_resend(group_id, execution_id)
        try:
            NoticeMain(payload['notice_group_id']).notice_task_group(payload['report'])
        except Exception:
            # 手动重发失败恢复原状态，不能变成自动待发送而绕过失败通知配置。
            ScheduledTaskGroupExecution.objects.filter(
                id=execution_id, notice_status=TestSuiteNoticeEnum.SENDING.value,
            ).update(notice_status=payload['previous_status'], update_time=timezone.now())
            raise
        ScheduledTaskGroupExecution.objects.filter(
            id=execution_id, notice_status=TestSuiteNoticeEnum.SENDING.value,
        ).update(notice_status=TestSuiteNoticeEnum.SENT.value, update_time=timezone.now())

    @classmethod
    @transaction.atomic
    def _claim_resend(cls, group_id: int, execution_id: int) -> dict:
        execution = ScheduledTaskGroupExecution.objects.select_for_update().select_related(
            'project_product', 'project_product__project',
        ).filter(id=execution_id, task_group_id=group_id).first()
        if execution is None:
            raise TaskCenterError(SYSTEM_TASK_GROUP_TASK_CONFIG_INVALID, value=('执行批次不存在或不属于该任务组',))
        if execution.notice_status == TestSuiteNoticeEnum.SENDING.value:
            raise TaskCenterError(SYSTEM_TASK_GROUP_TASK_CONFIG_INVALID, value=('汇总通知正在发送，请勿重复提交',))
        if not execution.notice_group_id:
            raise TaskCenterError(SYSTEM_TASK_GROUP_TASK_CONFIG_INVALID, value=('该执行批次未配置通知组',))
        fires = list(ScheduleFire.objects.filter(group_execution=execution)
                     .select_related('test_suite', 'task').order_by('id'))
        suite_ids = [fire.test_suite_id for fire in fires if fire.test_suite_id]
        # 触发记录可能已结束，但原报告中的失败项正在重试；以当前明细为准。
        if (
                len(fires) < execution.expected_count
                or any(not cls._fire_completed(fire) for fire in fires)
                or any(fire.test_suite.status not in cls.TERMINAL_SUITE_STATUSES
                       for fire in fires if fire.test_suite_id)
                or TestSuiteDetails.objects.filter(test_suite_id__in=suite_ids)
                .exclude(status__in=cls.TERMINAL_SUITE_STATUSES).exists()
        ):
            raise TaskCenterError(SYSTEM_TASK_GROUP_TASK_CONFIG_INVALID,
                                  value=('仍有子任务或用例未完成，请完成后再发送',))
        if not suite_ids:
            raise TaskCenterError(SYSTEM_TASK_GROUP_TASK_CONFIG_INVALID, value=('该执行批次没有可发送的执行报告',))
        report = cls._build_report(execution, [fire for fire in fires if fire.test_suite_id])
        previous_status = execution.notice_status
        execution.notice_status = TestSuiteNoticeEnum.SENDING.value
        execution.save(update_fields=['notice_status', 'update_time'])
        return {'notice_group_id': execution.notice_group_id, 'report': report,
                'previous_status': previous_status}

    @staticmethod
    def _finalize_empty_execution(execution) -> None:
        # 空批次没有可执行内容，必须结束；否则补偿任务会每 3 分钟刷新 update_time，
        # 批次永远停留在“进行中”，前端耗时也会一直增长。
        execution.status = TaskEnum.FAIL.value
        execution.finished_at = execution.finished_at or timezone.now()
        execution.notice_status = TestSuiteNoticeEnum.EXPIRED.value
        execution.save(update_fields=[
            'completed_count', 'status', 'finished_at', 'notice_status', 'update_time',
        ])

    @classmethod
    @transaction.atomic
    def _claim_notice(cls, execution_id: int) -> dict | None:
        execution = ScheduledTaskGroupExecution.objects.select_for_update().select_related(
            'project_product',
            'project_product__project',
        ).filter(id=execution_id).first()
        if execution is None:
            return None
        if execution.notice_status == TestSuiteNoticeEnum.SENDING.value:
            return None
        fires = list(
            ScheduleFire.objects.filter(group_execution=execution)
            .select_related('test_suite', 'task')
            .order_by('id')
        )
        completed = sum(1 for fire in fires if cls._fire_completed(fire))
        execution.completed_count = completed
        if not fires:
            cls._finalize_empty_execution(execution)
            return None
        if completed < execution.expected_count:
            execution.save(update_fields=['completed_count', 'update_time'])
            return None

        # 没有生成测试套的触发记录只用于确认批次已经结束，不进入通知。
        # 通知中的任务数、状态和用例统计只反映真实生成的执行报告。
        report_fires = [fire for fire in fires if fire.test_suite_id]
        batch_failed_task_count = sum(1 for fire in fires if cls._fire_failed(fire))
        failed_task_count = sum(1 for fire in report_fires if cls._fire_failed(fire))
        warning_task_count = sum(
            1
            for fire in report_fires
            if (
                    not cls._fire_failed(fire)
                    and fire.test_suite.status == TaskEnum.WARNING.value
            )
        )
        execution.status = (
            TaskEnum.FAIL.value
            if batch_failed_task_count
            else TaskEnum.WARNING.value if warning_task_count else TaskEnum.SUCCESS.value
        )
        blocked_reports = [fire for fire in report_fires
                           if fire.test_suite.status == TaskEnum.INFRASTRUCTURE_BLOCKED.value]
        if blocked_reports and not batch_failed_task_count:
            execution.status = TaskEnum.INFRASTRUCTURE_BLOCKED.value
        execution.finished_at = execution.finished_at or timezone.now()

        suite_ids = [fire.test_suite_id for fire in report_fires]
        if suite_ids:
            TestSuite.objects.filter(id__in=suite_ids).update(
                is_notice=TestSuiteNoticeEnum.EXPIRED.value,
            )

        should_notice = bool(
            report_fires
            and execution.is_notice
            and execution.notice_group_id
        )
        if execution.fail_notice == StatusEnum.SUCCESS.value and failed_task_count == 0:
            should_notice = False
        if blocked_reports and not failed_task_count:
            should_notice = False
        if not should_notice:
            execution.notice_status = TestSuiteNoticeEnum.EXPIRED.value
            execution.save(update_fields=[
                'completed_count', 'status', 'finished_at', 'notice_status', 'update_time',
            ])
            return None
        if execution.notice_status != TestSuiteNoticeEnum.NOT_SENT.value:
            execution.save(update_fields=['completed_count', 'status', 'finished_at', 'update_time'])
            return None

        report = cls._build_report(execution, report_fires)
        execution.notice_status = TestSuiteNoticeEnum.SENDING.value
        execution.save(update_fields=[
            'completed_count', 'status', 'finished_at', 'notice_status', 'update_time',
        ])
        return {'notice_group_id': execution.notice_group_id, 'report': report}

    @classmethod
    def retry_pending_notices(cls) -> int:
        ScheduledTaskGroupExecution.objects.filter(
            notice_status=TestSuiteNoticeEnum.SENDING.value,
            update_time__lt=timezone.now() - timedelta(minutes=10),
        ).update(
            notice_status=TestSuiteNoticeEnum.NOT_SENT.value,
            update_time=timezone.now(),
        )
        execution_ids = list(
            ScheduledTaskGroupExecution.objects.filter(
                notice_status=TestSuiteNoticeEnum.NOT_SENT.value,
            ).values_list('id', flat=True)
        )
        sent = 0
        for execution_id in execution_ids:
            try:
                sent += int(cls.try_finalize(execution_id))
            except Exception as error:
                log.system.error(
                    f'scheduler-service 发送任务组汇总通知失败：execution={execution_id}, error={error}'
                )
        return sent

    @classmethod
    def _build_report(
            cls,
            execution: ScheduledTaskGroupExecution,
            fires: list[ScheduleFire],
    ) -> TaskGroupNoticeReport:
        fires = [fire for fire in fires if fire.test_suite_id]
        counter_keys = [
            'case_sum', 'success', 'fail', 'warning',
            'api_case_sum', 'api_fail', 'ui_case_sum', 'ui_fail',
            'pytest_case_sum', 'pytest_fail',
            'excluded_count',
        ]
        counters = {key: 0 for key in counter_keys}
        child_reports = []
        suites = [fire.test_suite for fire in fires if fire.test_suite_id]
        failed_task_count = 0
        warning_task_count = 0

        for fire in fires:
            summary = {}
            summary_failed = False
            if fire.test_suite_id:
                try:
                    summary = TestSuiteSummaryService.counter_data(fire.test_suite_id)
                except Exception as error:
                    summary_failed = True
                    log.system.error(
                        f'汇总任务组子任务报告失败：'
                        f'test_suite={fire.test_suite_id}, error={error}'
                    )
            for key in counter_keys:
                counters[key] += int(summary.get(key) or 0)

            fire_failed = summary_failed or int(summary.get('fail') or 0) > 0 or (
                cls._fire_failed(fire) and not summary.get('excluded_count') and not summary.get('blocked')
            )
            fire_warning = bool(
                not fire_failed
                and fire.test_suite_id
                and (int(summary.get('warning') or 0) > 0 or (
                    fire.test_suite.status == TaskEnum.WARNING.value and not summary.get('excluded_count')
                ))
            )
            synthetic_failure = fire_failed and int(summary.get('fail') or 0) == 0
            if synthetic_failure:
                counters['case_sum'] += 1
                counters['fail'] += 1
            if fire_failed:
                failed_task_count += 1
                result = '失败'
            elif fire.test_suite.status == TaskEnum.INFRASTRUCTURE_BLOCKED.value or summary.get('blocked'):
                result = '平台受阻'
            elif fire_warning:
                warning_task_count += 1
                result = '告警'
            else:
                result = '成功'
            child_reports.append(TaskGroupChildReport(
                task_name=fire.task_name or (fire.task.name if fire.task else '未知子任务'),
                result=result,
                test_suite_id=(None if (
                    getattr(fire.test_suite, 'retained_summary', None)
                    or (getattr(fire.test_suite, 'report_retention_policy', None) == ReportRetentionPolicyEnum.ABNORMAL_ONLY.value
                        and fire.test_suite.status == TaskEnum.SUCCESS.value
                        and not summary.get('excluded_count') and not summary.get('fail') and not summary.get('warning'))
                ) else fire.test_suite_id),
                case_sum=int(summary.get('case_sum') or synthetic_failure),
                success=int(summary.get('success') or 0),
                fail=int(summary.get('fail') or synthetic_failure),
                warning=int(summary.get('warning') or 0),
            ))

        started_at = min((suite.create_time for suite in suites), default=execution.create_time)
        finished_candidates = [
            *(suite.update_time for suite in suites),
            *(fire.update_time for fire in fires if not fire.test_suite_id),
        ]
        finished_at = max(finished_candidates, default=execution.finished_at or timezone.now())
        total_seconds = max(0, int((finished_at - started_at).total_seconds()))
        success_rate = (
            100
            if counters['case_sum'] == 0
            else round(counters['success'] / counters['case_sum'] * 100, 2)
        )
        success_task_count = max(
            len(fires) - failed_task_count - warning_task_count,
            0,
        )
        return TaskGroupNoticeReport(
            execution_id=execution.id,
            task_group_name=execution.task_group_name,
            project_name=execution.project_product.project.name,
            product_name=execution.project_product.name,
            test_environment=EnvironmentEnum.get_value(execution.test_env),
            planned_at=execution.planned_at.strftime('%Y-%m-%d %H:%M:%S'),
            execution_duration=(
                f'{total_seconds // 3600:02d}:'
                f'{(total_seconds % 3600) // 60:02d}:'
                f'{total_seconds % 60:02d}'
            ),
            task_count=len(fires),
            completed_task_count=len(fires),
            success_task_count=success_task_count,
            failed_task_count=failed_task_count,
            warning_task_count=warning_task_count,
            success_rate=success_rate,
            children=child_reports,
            **counters,
        )

    @classmethod
    def _fire_completed(cls, fire: ScheduleFire) -> bool:
        if fire.status in cls.TERMINAL_FIRE_STATUSES:
            return True
        return bool(
            fire.test_suite_id
            and fire.test_suite.status in cls.TERMINAL_SUITE_STATUSES
        )

    @classmethod
    def _fire_failed(cls, fire: ScheduleFire) -> bool:
        # 报告重试后以当前结果为准，不能沿用首次执行留下的失败触发状态。
        if fire.test_suite_id:
            return fire.test_suite.status in (TaskEnum.FAIL.value, TaskEnum.STOPPED.value)
        if fire.status in cls.TERMINAL_FIRE_STATUSES:
            return True
        return False
