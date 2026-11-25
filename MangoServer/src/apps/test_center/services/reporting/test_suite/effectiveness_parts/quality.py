from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta

from django.db.models import Count, Max
from django.utils import timezone
from mangotools.enums import TaskEnum

from src.apps.task_center.enums.execution import (
    AutomationExecutionSceneEnum,
    AutomationExecutionScopeEnum,
)
from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.enums.environment import EnvironmentEnum
from src.apps.test_center.services.reporting.test_suite.summary import TestSuiteSummaryService

logger = logging.getLogger(__name__)


class AutomationEffectivenessQualityMixin:
    @classmethod
    def _benefits(cls, suites, details, executions, cards, convergence) -> dict:
        detail_rows = list(details.values(
            'id',
            'test_suite_id',
            'test_suite__tasks_id',
            'test_suite__create_time',
            'test_suite__execution_scenes',
            'type',
            'case_id',
            'case_sum',
            'status',
            'success',
            'fail',
            'warning',
        ))
        suite_rows = list(suites.values(
            'execution_scenes',
            'project_product_id',
            'module_id',
            'test_env',
            'create_time',
        ))
        status_counts = TestSuiteSummaryService.execution_status_counts_from_rows(detail_rows)
        first_failed_ids = set(
            executions.filter(attempt_no=1, status=TaskEnum.FAIL.value)
            .values_list('test_suite_detail_id', flat=True)
            .distinct()
        )
        latest_success_ids = set(
            executions.filter(is_latest=True, status=TaskEnum.SUCCESS.value)
            .values_list('test_suite_detail_id', flat=True)
            .distinct()
        )
        retry_recovered_ids = first_failed_ids & latest_success_ids
        scene_suites = defaultdict(list)
        scene_details = defaultdict(list)
        for item in suite_rows:
            for scene in item['execution_scenes'] or []:
                scene_suites[scene].append(item)
        for item in detail_rows:
            for scene in item['test_suite__execution_scenes'] or []:
                scene_details[scene].append(item)

        scene_benefits = []
        for scene in AutomationExecutionSceneEnum:
            if scene == AutomationExecutionSceneEnum.UNCLASSIFIED:
                continue
            scene_suite_rows = scene_suites.get(scene.value, [])
            scene_detail_rows = scene_details.get(scene.value, [])
            if not scene_suite_rows and not scene_detail_rows:
                continue
            scene_counts = TestSuiteSummaryService.execution_status_counts_from_rows(
                scene_detail_rows
            )
            scene_benefits.append({
                'scene': scene.value,
                'name': AutomationExecutionSceneEnum.get_value(scene.value),
                'suite_count': len(scene_suite_rows),
                'execution_count': sum(scene_counts.values()),
                'unique_case_count': TestSuiteSummaryService.unique_case_count_from_rows(
                    scene_detail_rows
                ),
                'success_count': scene_counts['success'],
                'abnormal_count': scene_counts['fail'] + scene_counts['warning'],
                'active_day_count': cls._active_day_count(scene_suite_rows),
            })

        type_counts = defaultdict(int)
        for item in detail_rows:
            type_counts[item['type']] += TestSuiteSummaryService.effective_case_sum(item)
        return {
            'report_count': cards['suite_count'],
            'execution_count': sum(status_counts.values()),
            'unique_case_count': TestSuiteSummaryService.unique_case_count_from_rows(detail_rows),
            'detected_issue_count': status_counts['fail'] + status_counts['warning'],
            'abnormal_result_count': status_counts['fail'] + status_counts['warning'],
            'affected_case_count': convergence['affected_case_count'],
            'retry_recovered_count': sum(
                TestSuiteSummaryService.effective_case_sum(item)
                for item in detail_rows
                if item['id'] in retry_recovered_ids
            ),
            'period_recovered_case_count': convergence['recovered_case_count'],
            'active_day_count': cls._active_day_count(suite_rows),
            'project_product_count': len({
                item['project_product_id'] for item in suite_rows
                if item['project_product_id'] is not None
            }),
            'module_count': len({
                item['module_id'] for item in suite_rows
                if item['module_id'] is not None
            }),
            'environment_count': len({
                item['test_env'] for item in suite_rows
                if item['test_env'] is not None
            }),
            'p95_first_feedback_seconds': cards['p95_first_feedback_seconds'],
            'p95_feedback_seconds': cards['p95_feedback_seconds'],
            'feedback_sample_count': cards['feedback_sample_count'],
            'feedback_report_count': cards['feedback_report_count'],
            'feedback_sample_coverage': cards['feedback_sample_coverage'],
            'scene_benefits': scene_benefits,
            'automation_types': [
                {
                    'type': case_type.value,
                    'name': TestCaseTypeEnum.get_value(case_type.value) or '其他自动化',
                    'count': type_counts[case_type.value],
                }
                for case_type in TestCaseTypeEnum
                if type_counts[case_type.value]
            ],
        }

    @staticmethod
    def _active_day_count(suite_rows: list[dict]) -> int:
        active_days = set()
        for item in suite_rows:
            created_at = item.get('create_time')
            if created_at is None:
                continue
            if timezone.is_aware(created_at):
                created_at = timezone.localtime(created_at)
            active_days.add(created_at.date())
        return len(active_days)

    @classmethod
    def _convergence(cls, details, previous_details) -> dict:
        issue_statuses = (TaskEnum.FAIL.value, TaskEnum.WARNING.value)
        current_rows = list(details.values(
            'type', 'case_id', 'case_sum', 'status', 'success', 'fail', 'warning',
            'test_suite__create_time'
        ).order_by('type', 'case_id', '-test_suite__create_time'))
        previous_rows = list(previous_details.values(
            'type', 'case_id', 'case_sum', 'status', 'success', 'fail', 'warning'
        ))
        current_issue_cases = {
            (item['type'], item['case_id'])
            for item in current_rows
            if item['status'] in issue_statuses
        }
        previous_issue_cases = {
            (item['type'], item['case_id'])
            for item in previous_rows
            if item['status'] in issue_statuses
        }
        latest_statuses = {}
        for item in current_rows:
            latest_statuses.setdefault((item['type'], item['case_id']), item['status'])
        recovered_cases = {
            case_key for case_key in previous_issue_cases
            if latest_statuses.get(case_key) == TaskEnum.SUCCESS.value
        }
        current_case_sums = TestSuiteSummaryService.unique_case_sums_from_rows(current_rows)
        previous_case_sums = TestSuiteSummaryService.unique_case_sums_from_rows(previous_rows)
        current_counts = TestSuiteSummaryService.execution_status_counts_from_rows(
            current_rows
        )
        previous_counts = TestSuiteSummaryService.execution_status_counts_from_rows(
            previous_rows
        )
        current_completed = TestSuiteSummaryService.completed_execution_count(current_counts)
        previous_completed = TestSuiteSummaryService.completed_execution_count(previous_counts)
        current_issue_count = current_counts['fail'] + current_counts['warning']
        previous_issue_count = previous_counts['fail'] + previous_counts['warning']
        current_issue_rate = cls._rate(current_issue_count, current_completed)
        previous_issue_rate = cls._rate(previous_issue_count, previous_completed)
        issue_rate_delta = None
        if current_issue_rate is not None and previous_issue_rate is not None:
            issue_rate_delta = round(current_issue_rate - previous_issue_rate, 2)
        direction = 'unknown'
        if issue_rate_delta is not None:
            direction = 'stable' if abs(issue_rate_delta) < 0.1 else (
                'converging' if issue_rate_delta < 0 else 'diverging'
            )
        return {
            'direction': direction,
            'current_issue_count': current_issue_count,
            'previous_issue_count': previous_issue_count,
            'issue_count_delta': current_issue_count - previous_issue_count,
            'current_issue_rate': current_issue_rate,
            'previous_issue_rate': previous_issue_rate,
            'issue_rate_delta': issue_rate_delta,
            'affected_case_count': sum(
                current_case_sums[case_key] for case_key in current_issue_cases
            ),
            'new_issue_case_count': sum(
                current_case_sums[case_key]
                for case_key in current_issue_cases - previous_issue_cases
            ),
            'recovered_case_count': sum(
                previous_case_sums[case_key] for case_key in recovered_cases
            ),
        }

    @classmethod
    def _environment_quality(cls, suites, details, executions) -> list[dict]:
        suite_counts = {
            item['test_env']: item['count']
            for item in suites.values('test_env').annotate(count=Count('id'))
        }
        rows_by_environment = defaultdict(list)
        for item in details.values(
                'test_suite__test_env', 'case_sum', 'status', 'success', 'fail', 'warning'
        ):
            rows_by_environment[item['test_suite__test_env']].append(item)
        duration_rows = {
            item['test_suite__test_env']: item['duration'] or 0
            for item in executions.values('test_suite__test_env').annotate(duration=Max('duration'))
        }
        rows = []
        for env in EnvironmentEnum:
            env_id = env.value
            counts = TestSuiteSummaryService.execution_status_counts_from_rows(
                rows_by_environment.get(env_id, [])
            )
            total = sum(counts.values())
            completed = TestSuiteSummaryService.completed_execution_count(counts)
            rows.append({
                'environment': env_id,
                'environment_name': EnvironmentEnum.get_value(env_id),
                'suite_count': suite_counts.get(env_id, 0),
                'detail_count': total,
                'final_pass_rate': cls._rate(counts['success'], completed),
                'completion_rate': cls._rate(completed, total),
                'failed_count': counts['fail'],
                'warning_count': counts['warning'],
                'unfinished_count': counts['stay_begin'] + counts['proceed'],
                'max_case_duration_seconds': round(duration_rows.get(env_id, 0), 2),
            })
        return sorted(
            (item for item in rows if item['suite_count'] > 0),
            key=lambda item: (
                item['final_pass_rate'] is None,
                -(item['final_pass_rate'] or 0),
                -item['detail_count'],
            ),
        )

    @classmethod
    def _trend(cls, details, start_at: datetime, end_at: datetime) -> list[dict]:
        rows_by_day = defaultdict(list)
        for item in details.values(
                'test_suite__create_time', 'case_sum', 'status', 'success', 'fail', 'warning'
        ):
            rows_by_day[cls._local_date(item['test_suite__create_time'])].append(item)
        detail_rows = {}
        for day, rows in rows_by_day.items():
            counts = TestSuiteSummaryService.execution_status_counts_from_rows(rows)
            detail_rows[day] = {
                'total': sum(counts.values()),
                'completed': TestSuiteSummaryService.completed_execution_count(counts),
                'success': counts['success'],
                'failed': counts['fail'],
                'warning': counts['warning'],
            }
        return cls._complete_trend_days(detail_rows, start_at, end_at)

    @classmethod
    def _complete_trend_days(cls, detail_rows, start_at: datetime, end_at: datetime) -> list[dict]:
        start_day = cls._local_date(start_at)
        end_day = cls._local_date(end_at - timedelta(microseconds=1))
        result = []
        current_day = start_day
        while current_day <= end_day:
            detail = detail_rows.get(current_day, {})
            result.append({
                'date': current_day.strftime('%m-%d'),
                'date_value': current_day.isoformat(),
                'detail_count': detail.get('total', 0),
                'failed_count': detail.get('failed', 0),
                'warning_count': detail.get('warning', 0),
                'final_pass_rate': cls._rate(
                    detail.get('success', 0),
                    detail.get('completed', 0),
                ),
            })
            current_day += timedelta(days=1)
        return result

    @staticmethod
    def _local_date(value: datetime):
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        return value.date()

    @classmethod
    def _status_distribution(cls, details) -> list[dict]:
        counts = TestSuiteSummaryService.execution_status_counts_from_rows(
            details.values('case_sum', 'status', 'success', 'fail', 'warning')
        )
        status_keys = {
            TaskEnum.SUCCESS.value: 'success',
            TaskEnum.FAIL.value: 'fail',
            TaskEnum.WARNING.value: 'warning',
            TaskEnum.PROCEED.value: 'proceed',
            TaskEnum.STAY_BEGIN.value: 'stay_begin',
            TaskEnum.STOPPED.value: 'stopped',
            TaskEnum.INFRASTRUCTURE_BLOCKED.value: 'blocked',
        }
        return [
            {
                'status': status.value,
                'name': TaskEnum.get_value(status.value),
                'value': counts[status_keys[status.value]],
            }
            for status in TaskEnum if status != TaskEnum.INFRASTRUCTURE_BLOCKED
        ]

    @classmethod
    def _scene_distribution(cls, details) -> list[dict]:
        grouped = defaultdict(list)
        for item in details.values(
                'test_suite__execution_scenes', 'case_sum', 'status', 'success', 'fail', 'warning'
        ):
            for scene in item['test_suite__execution_scenes'] or []:
                grouped[scene].append(item)
        result = []
        for scene, rows in grouped.items():
            counts = TestSuiteSummaryService.execution_status_counts_from_rows(rows)
            completed = TestSuiteSummaryService.completed_execution_count(counts)
            result.append({
                'scene': scene,
                'scene_name': AutomationExecutionSceneEnum.get_value(
                    scene
                ) or '未分类',
                'detail_count': sum(counts.values()),
                'success_count': counts['success'],
                'failed_count': counts['fail'],
                'warning_count': counts['warning'],
                'final_pass_rate': cls._rate(counts['success'], completed),
            })
        return sorted(result, key=lambda item: -item['detail_count'])

    @classmethod
    def _scope_distribution(cls, details) -> list[dict]:
        grouped = defaultdict(list)
        for item in details.values(
                'test_suite__execution_scope', 'case_sum', 'status', 'success', 'fail', 'warning'
        ):
            grouped[item['test_suite__execution_scope']].append(item)
        result = []
        for scope, rows in grouped.items():
            counts = TestSuiteSummaryService.execution_status_counts_from_rows(rows)
            completed = TestSuiteSummaryService.completed_execution_count(counts)
            result.append({
                'scope': scope,
                'scope_name': AutomationExecutionScopeEnum.get_value(
                    scope
                ) or '未分类',
                'detail_count': sum(counts.values()),
                'success_count': counts['success'],
                'failed_count': counts['fail'],
                'warning_count': counts['warning'],
                'final_pass_rate': cls._rate(counts['success'], completed),
            })
        return sorted(result, key=lambda item: -item['detail_count'])

    @classmethod
    def _insights(cls, cards, environments, inspection_tasks, module_risks) -> list[dict]:
        insights = []
        if not cards['suite_count']:
            return [{
                'level': 'info',
                'title': '当前筛选范围没有正式定时报告',
                'description': '手动批量执行不会进入自动化效能统计。',
            }]
        abnormal_inspections = [
            item for item in inspection_tasks
            if item['consecutive_failures'] > 0 or item['failed_count'] > 0
        ]
        if abnormal_inspections:
            worst = abnormal_inspections[0]
            insights.append({
                'level': 'danger',
                'title': f"{len(abnormal_inspections)} 个巡检任务当前存在异常",
                'description': (
                    f"{worst['task_name']} 已连续失败 {worst['consecutive_failures']} 次，"
                    f"最近报告 {worst['latest_suite_id']}。"
                ),
            })
        if cards['unfinished_count']:
            insights.append({
                'level': 'warning',
                'title': f"{cards['unfinished_count']} 个执行明细尚未结束",
                'description': '请关注长期处于待开始或进行中的定时报告。',
            })
        if (
                cards['flaky_rate'] is not None
                and cards['flaky_rate'] > cls.HEALTHY_FLAKY_RATE
        ):
            insights.append({
                'level': 'warning',
                'title': (
                    f"执行不稳定率 {cards['flaky_rate']:.2f}%，"
                    f"超过健康阈值 {cls.HEALTHY_FLAKY_RATE:.2f}%"
                ),
                'description': (
                    f"{cards['flaky_count']} 个用例首轮失败后通过重试恢复；"
                    '最终结果虽已通过，执行稳定性仍需关注。'
                ),
            })
        if module_risks:
            worst_module = module_risks[0]
            insights.append({
                'level': 'danger' if worst_module['failed_count'] else 'warning',
                'title': f"{len(module_risks)} 个模块存在质量异常",
                'description': (
                    f"{worst_module['module_path']} 失败 {worst_module['failed_count']} 次、"
                    f"警告 {worst_module['warning_count']} 次，"
                    f"最终通过率 {worst_module['final_pass_rate'] or 0:.2f}%。"
                ),
            })
        valid_environments = [
            item for item in environments if item['final_pass_rate'] is not None
        ]
        if valid_environments:
            worst_env = min(valid_environments, key=lambda item: item['final_pass_rate'])
            if worst_env['final_pass_rate'] < 98:
                insights.append({
                    'level': 'warning' if worst_env['final_pass_rate'] >= 90 else 'danger',
                    'title': f"{worst_env['environment_name']}质量最低",
                    'description': (
                        f"最终通过率 {worst_env['final_pass_rate']:.2f}%，"
                        f"包含 {worst_env['failed_count']} 个失败明细。"
                    ),
                })
        if cards['data_completeness'] is not None and cards['data_completeness'] < 80:
            insights.append({
                'level': 'info',
                'title': '部分历史报告缺少统一执行记录',
                'description': (
                    f"当前统一执行记录覆盖率为 {cards['data_completeness']:.2f}%，"
                    '部分历史结果可能无法完整参与波动与重试恢复分析。'
                ),
            })
        if not insights:
            insights.append({
                'level': 'success',
                'title': '当前自动化质量整体稳定',
                'description': '未发现未完成报告、巡检连续失败或明显低质量环境。',
            })
        return insights[:4]
