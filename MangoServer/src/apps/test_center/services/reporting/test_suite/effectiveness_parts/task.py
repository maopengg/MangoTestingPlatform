from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime

from django.db.models import Min
from django.utils import timezone
from mangotools.enums import TaskEnum
from math import ceil

from src.apps.task_center.enums.execution import (
    AutomationExecutionSceneEnum,
    AutomationExecutionScopeEnum,
)
from src.apps.task_center.models import Tasks
from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.enums.environment import EnvironmentEnum
from src.apps.test_center.models import ProductModule
from src.apps.test_center.services.project.product_module import ProductModuleService
from src.apps.test_center.services.reporting.test_suite.summary import TestSuiteSummaryService

logger = logging.getLogger(__name__)


class AutomationEffectivenessTaskMixin:
    @classmethod
    def _task_health(cls, suites, details) -> list[dict]:
        suite_rows = list(suites.values(
            'id',
            'tasks_id',
            'tasks__name',
            'tasks__diagnostic_file_path',
            'test_env',
            'execution_scenes',
            'execution_scope',
            'project_product__name',
            'module_id',
            'status',
            'create_time',
        ).order_by('tasks_id', '-create_time'))
        if not suite_rows:
            return []

        timing_names_by_task = {
            task.id: '、'.join(strategy.name for strategy in task.timing_strategies.all())
            for task in Tasks.objects.filter(
                id__in={item['tasks_id'] for item in suite_rows if item['tasks_id']}
            ).prefetch_related('timing_strategies')
        }

        detail_rows = list(details.values(
            'test_suite_id',
            'type',
            'case_id',
            'case_sum',
            'status',
            'success',
            'fail',
            'warning',
        ))
        details_by_suite = defaultdict(list)
        for detail in detail_rows:
            details_by_suite[detail['test_suite_id']].append(detail)

        module_ids = {item['module_id'] for item in suite_rows if item['module_id']}
        module_paths = {
            module.id: module.get_full_path()
            for module in ProductModuleService.with_full_paths(
                ProductModule.objects.filter(id__in=module_ids)
            )
        }
        grouped = defaultdict(list)
        for suite in suite_rows:
            grouped[suite['tasks_id']].append(suite)

        result = []
        for task_id, task_suites in grouped.items():
            latest = task_suites[0]
            task_detail_rows = [
                detail
                for suite in task_suites
                for detail in details_by_suite.get(suite['id'], [])
            ]
            counts = TestSuiteSummaryService.execution_status_counts_from_rows(
                task_detail_rows
            )
            completed = (
                    counts['success']
                    + counts['fail']
                    + counts['warning']
                    + counts['stopped']
            )
            consecutive_abnormal = 0
            for suite in task_suites:
                if suite['status'] == TaskEnum.SUCCESS.value:
                    break
                if suite['status'] in (TaskEnum.FAIL.value, TaskEnum.WARNING.value):
                    consecutive_abnormal += 1
            last_success = next(
                (
                    suite['create_time']
                    for suite in task_suites
                    if suite['status'] == TaskEnum.SUCCESS.value
                ),
                None,
            )
            report_completed_count = sum(
                1 for suite in task_suites if suite['status'] in cls.COMPLETED_STATUSES
            )
            report_success_count = sum(
                1 for suite in task_suites if suite['status'] == TaskEnum.SUCCESS.value
            )
            report_success_rate = cls._rate(
                report_success_count,
                report_completed_count,
            )
            final_pass_rate = cls._rate(counts['success'], completed)
            result.append({
                'task_id': task_id,
                'task_name': latest['tasks__name'] or f'定时任务 #{task_id}',
                'timing_strategy_name': timing_names_by_task.get(task_id, '-'),
                'diagnostic_file_path': latest['tasks__diagnostic_file_path'],
                'project_product_name': latest['project_product__name'],
                'module_name': module_paths.get(latest['module_id'], '全部模块'),
                'environment': latest['test_env'],
                'environment_name': EnvironmentEnum.get_value(latest['test_env']),
                'execution_scenes': latest['execution_scenes'] or [],
                'execution_scene_names': [
                    AutomationExecutionSceneEnum.get_value(scene) or scene
                    for scene in (latest['execution_scenes'] or [])
                ],
                'execution_scope': latest['execution_scope'],
                'execution_scope_name': AutomationExecutionScopeEnum.get_value(
                    latest['execution_scope']
                ) or '未分类',
                'suite_count': len(task_suites),
                'report_completed_count': report_completed_count,
                'report_success_count': report_success_count,
                'report_success_rate': report_success_rate,
                'execution_count': sum(counts.values()),
                'issue_count': counts['fail'] + counts['warning'],
                'final_pass_rate': final_pass_rate,
                'consecutive_abnormal': consecutive_abnormal,
                'latest_suite_id': latest['id'],
                'latest_status': latest['status'],
                'latest_time': cls._format_datetime(latest['create_time']),
                'last_success_time': cls._format_datetime(last_success) if last_success else None,
            })
        result.sort(key=lambda item: (
            -item['consecutive_abnormal'],
            item['final_pass_rate'] if item['final_pass_rate'] is not None else 101,
            -item['issue_count'],
        ))
        return result

    @staticmethod
    def _task_source_summary(task_health: list[dict]) -> dict:
        return {
            'task_count': len(task_health),
            'report_count': sum(int(item.get('suite_count') or 0) for item in task_health),
            'execution_count': sum(
                int(item.get('execution_count') or 0) for item in task_health
            ),
            'report_success_count': sum(
                int(item.get('report_success_count') or 0) for item in task_health
            ),
        }

    @classmethod
    def _failed_case_ranking(cls, details) -> list[dict]:
        rows = list(
            details.values(
                'id',
                'test_suite_id',
                'type',
                'case_id',
                'case_name',
                'status',
                'error_message',
                'test_suite__tasks_id',
                'test_suite__tasks__name',
                'test_suite__project_product__name',
                'test_suite__test_env',
                'test_suite__create_time',
            ).order_by(
                'test_suite__tasks_id',
                'type',
                'case_id',
                '-test_suite__create_time',
                '-id',
            )
        )
        grouped = defaultdict(list)
        for row in rows:
            task_id = row['test_suite__tasks_id']
            if not task_id:
                continue
            grouped[(task_id, row['type'], row['case_id'])].append(row)

        result = []
        for (task_id, case_type, case_id), case_rows in grouped.items():
            latest = case_rows[0]
            failed_rows = [
                row for row in case_rows if row['status'] == TaskEnum.FAIL.value
            ]
            if not failed_rows:
                continue
            latest_failed = failed_rows[0]
            failed_count = len(failed_rows)
            result.append({
                'task_id': task_id,
                'task_name': latest['test_suite__tasks__name'] or f'定时任务 #{task_id}',
                'case_type': case_type,
                'case_type_name': TestCaseTypeEnum.get_value(case_type) or '未知类型',
                'case_id': case_id,
                'case_name': latest['case_name'] or f'用例 #{case_id}',
                'project_product_name': latest['test_suite__project_product__name'],
                'environment': latest['test_suite__test_env'],
                'environment_name': EnvironmentEnum.get_value(
                    latest['test_suite__test_env']
                ),
                'attempt_count': len(case_rows),
                'failed_count': failed_count,
                'failure_rate': cls._rate(failed_count, len(case_rows)),
                'latest_failed_detail_id': latest_failed['id'],
                'latest_failed_suite_id': latest_failed['test_suite_id'],
                'latest_error': str(latest_failed['error_message'] or '')[:1000],
                'latest_time': cls._format_datetime(
                    latest_failed['test_suite__create_time']
                ),
            })

        result.sort(key=lambda item: (
            -item['failed_count'],
            -item['failure_rate'],
            item['case_name'],
        ))
        return result[:30]

    @classmethod
    def _inspection_tasks(cls, suites, details) -> list[dict]:
        inspection_suites = list(
            suites.filter(
                execution_scenes__contains=[AutomationExecutionSceneEnum.PRODUCTION_INSPECTION.value]
            )
            .values(
                'id',
                'tasks_id',
                'tasks__name',
                'test_env',
                'execution_scope',
                'project_product__name',
                'module_id',
                'status',
                'create_time',
            )
            .order_by('tasks_id', '-create_time')
        )
        if not inspection_suites:
            return []

        timing_names_by_task = {
            task.id: '、'.join(strategy.name for strategy in task.timing_strategies.all())
            for task in Tasks.objects.filter(
                id__in={item['tasks_id'] for item in inspection_suites if item['tasks_id']}
            ).prefetch_related('timing_strategies')
        }

        module_ids = {
            item['module_id'] for item in inspection_suites if item['module_id']
        }
        module_paths = {
            module.id: module.get_full_path()
            for module in ProductModuleService.with_full_paths(
                ProductModule.objects.filter(id__in=module_ids)
            )
        }

        details_by_suite = defaultdict(list)
        for item in details.filter(
                test_suite_id__in=[suite['id'] for suite in inspection_suites]
        ).values(
            'test_suite_id', 'case_sum', 'status', 'success', 'fail', 'warning'
        ):
            details_by_suite[item['test_suite_id']].append(item)
        grouped = defaultdict(list)
        for suite in inspection_suites:
            grouped[suite['tasks_id']].append(suite)

        result = []
        for task_id, task_suites in grouped.items():
            latest = task_suites[0]
            consecutive_failures = 0
            last_success_time = None
            for suite in task_suites:
                if suite['status'] == TaskEnum.SUCCESS.value:
                    if last_success_time is None:
                        last_success_time = suite['create_time']
                    if suite is not latest:
                        break
                elif last_success_time is None:
                    consecutive_failures += 1
            counts = TestSuiteSummaryService.execution_status_counts_from_rows(
                details_by_suite.get(latest['id'], [])
            )
            completed = counts['success'] + counts['fail'] + counts['warning'] + counts['stopped']
            result.append({
                'task_id': task_id,
                'task_name': latest['tasks__name'],
                'timing_strategy_name': timing_names_by_task.get(task_id, '-'),
                'environment': latest['test_env'],
                'environment_name': EnvironmentEnum.get_value(latest['test_env']),
                'execution_scope': latest['execution_scope'],
                'execution_scope_name': AutomationExecutionScopeEnum.get_value(latest['execution_scope']),
                'project_product_name': latest['project_product__name'],
                'module_name': module_paths.get(latest['module_id'], '项目全量'),
                'latest_suite_id': latest['id'],
                'latest_status': latest['status'],
                'latest_time': cls._format_datetime(latest['create_time']),
                'last_success_time': (
                    cls._format_datetime(last_success_time)
                    if last_success_time else None
                ),
                'consecutive_failures': consecutive_failures,
                'detail_count': sum(counts.values()),
                'failed_count': counts['fail'],
                'final_pass_rate': cls._rate(counts['success'], completed),
            })
        result.sort(key=lambda item: (-item['consecutive_failures'], item['final_pass_rate']))
        return result[:100]

    @classmethod
    def _first_feedback_metrics(cls, suites, details, executions) -> dict:
        suite_rows = list(suites.values('id', 'create_time'))
        detail_rows = list(details.values('id', 'test_suite_id'))
        first_result_rows = list(
            executions.filter(
                attempt_no=1,
                test_suite_detail_id__isnull=False,
            )
            .values('test_suite_detail_id', 'test_suite_detail__test_suite_id')
            .annotate(first_result_at=Min('create_time'))
        )
        return cls._first_feedback_metrics_from_rows(
            suite_rows,
            detail_rows,
            first_result_rows,
        )

    @classmethod
    def _first_feedback_metrics_from_rows(
            cls,
            suite_rows: list[dict],
            detail_rows: list[dict],
            first_result_rows: list[dict],
    ) -> dict:
        expected_detail_ids = defaultdict(set)
        for item in detail_rows:
            expected_detail_ids[item['test_suite_id']].add(item['id'])
        first_results = defaultdict(dict)
        for item in first_result_rows:
            detail_id = item.get('test_suite_detail_id')
            suite_id = item.get('test_suite_detail__test_suite_id')
            result_at = item.get('first_result_at')
            if detail_id is not None and suite_id is not None and result_at is not None:
                first_results[suite_id][detail_id] = result_at

        durations = []
        for suite in suite_rows:
            suite_id = suite['id']
            expected_ids = expected_detail_ids.get(suite_id) or set()
            result_map = first_results.get(suite_id) or {}
            if not expected_ids or not expected_ids.issubset(result_map):
                continue
            completed_at = max(result_map[detail_id] for detail_id in expected_ids)
            durations.append(max((completed_at - suite['create_time']).total_seconds(), 0))
        report_count = len(suite_rows)
        sample_count = len(durations)
        return {
            'p95_seconds': cls._percentile(durations, 95),
            'sample_count': sample_count,
            'report_count': report_count,
            'sample_coverage': cls._rate(sample_count, report_count),
        }

    @staticmethod
    def _rate(numerator: int, denominator: int) -> float | None:
        if not denominator:
            return None
        return round(numerator / denominator * 100, 2)

    @staticmethod
    def _percentile(values: list[float], percentile: int) -> float | None:
        if not values:
            return None
        ordered = sorted(values)
        index = max(ceil(len(ordered) * percentile / 100) - 1, 0)
        return round(ordered[index], 2)

    @staticmethod
    def _format_datetime(value: datetime) -> str:
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        return value.strftime('%Y-%m-%d %H:%M:%S')
