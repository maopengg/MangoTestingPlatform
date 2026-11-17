from __future__ import annotations

import logging
from collections import defaultdict

from mangotools.enums import TaskEnum

from src.apps.task_center.enums.execution import (
    AutomationExecutionSceneEnum,
)
from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.enums.environment import EnvironmentEnum
from src.apps.test_center.models import ProductModule
from src.apps.test_center.services.project.product_module import ProductModuleService
from src.apps.test_center.services.reporting.test_suite.summary import TestSuiteSummaryService

logger = logging.getLogger(__name__)


class AutomationEffectivenessModuleMixin:
    @classmethod
    def _aggregate_module_quality(cls, details) -> list[dict]:
        rows = list(details.values(
            'type',
            'case_id',
            'case_sum',
            'status',
            'test_suite_id',
            'test_suite__tasks_id',
            'test_suite__create_time',
            'test_suite__module_id',
            'test_suite__project_product_id',
            'test_suite__project_product__name',
            'test_suite__project_product__project__name',
        ))
        if not rows:
            return []

        module_ids = {
            row['test_suite__module_id']
            for row in rows
            if row['test_suite__module_id']
        }
        modules = ProductModuleService.with_full_paths(
            ProductModule.objects.filter(id__in=module_ids)
            .select_related('project_product', 'project_product__project')
        )
        module_map = {module.id: module for module in modules}

        grouped = {}
        for row in rows:
            module_id = row['test_suite__module_id']
            module = module_map.get(module_id)
            group_key = (
                f'module:{module_id}'
                if module_id
                else f"all:{row['test_suite__project_product_id']}"
            )
            item = grouped.setdefault(group_key, {
                'module_key': group_key,
                'module_id': module_id,
                'module_path': module.get_full_path() if module else '全部模块',
                'project_name': (
                    module.project_product.project.name
                    if module else row['test_suite__project_product__project__name']
                ),
                'project_product_name': (
                    module.project_product.name
                    if module else row['test_suite__project_product__name']
                ),
                'detail_count': 0,
                'completed_count': 0,
                'success_count': 0,
                'failed_count': 0,
                'warning_count': 0,
                'suite_ids': set(),
                'case_rows': [],
                'scope_types': set(),
                'latest_failed_suite_id': None,
                'latest_failed_time': None,
                'latest_issue_suite_id': None,
                'latest_issue_time': None,
            })
            item['suite_ids'].add(row['test_suite_id'])
            item['case_rows'].append(row)
            item['scope_types'].add(
                '全部模块' if row['test_suite__module_id'] is None else '指定模块'
            )
            row_counts = TestSuiteSummaryService.execution_status_counts_from_rows([row])
            item['detail_count'] += sum(row_counts.values())
            item['completed_count'] += TestSuiteSummaryService.completed_execution_count(row_counts)
            item['success_count'] += row_counts['success']
            item['failed_count'] += row_counts['fail']
            item['warning_count'] += row_counts['warning']
            if row_counts['fail']:
                if (
                        item['latest_failed_time'] is None
                        or row['test_suite__create_time'] > item['latest_failed_time']
                ):
                    item['latest_failed_time'] = row['test_suite__create_time']
                    item['latest_failed_suite_id'] = row['test_suite_id']
            if (row_counts['fail'] or row_counts['warning']) and (
                    item['latest_issue_time'] is None
                    or row['test_suite__create_time'] > item['latest_issue_time']
            ):
                item['latest_issue_time'] = row['test_suite__create_time']
                item['latest_issue_suite_id'] = row['test_suite_id']

        result = []
        for item in grouped.values():
            scope_types = item.pop('scope_types')
            item['execution_scope_name'] = ' + '.join(
                scope for scope in ('全部模块', '指定模块') if scope in scope_types
            )
            item['suite_count'] = len(item.pop('suite_ids'))
            item['case_count'] = TestSuiteSummaryService.unique_case_count_from_rows(
                item.pop('case_rows')
            )
            item['final_pass_rate'] = cls._rate(
                item.pop('success_count'),
                item.pop('completed_count'),
            )
            item['latest_failed_time'] = (
                cls._format_datetime(item['latest_failed_time'])
                if item['latest_failed_time'] else None
            )
            item['latest_issue_time'] = (
                cls._format_datetime(item['latest_issue_time'])
                if item['latest_issue_time'] else None
            )
            result.append(item)
        result.sort(key=lambda item: (
            0 if item['failed_count'] or item['warning_count'] else 1,
            -item['failed_count'],
            -item['warning_count'],
            item['final_pass_rate'] if item['final_pass_rate'] is not None else 101,
        ))
        return result

    @classmethod
    def _module_quality(cls, details, previous_details) -> list[dict]:
        current_items = cls._aggregate_module_quality(details)
        previous_map = {
            item['module_key']: item
            for item in cls._aggregate_module_quality(previous_details)
        }
        for item in current_items:
            previous = previous_map.get(item['module_key'])
            previous_rate = previous['final_pass_rate'] if previous else None
            item['previous_final_pass_rate'] = previous_rate
            item['pass_rate_delta'] = (
                round(item['final_pass_rate'] - previous_rate, 2)
                if item['final_pass_rate'] is not None and previous_rate is not None
                else None
            )
            if item['failed_count'] or (
                    item['final_pass_rate'] is not None and item['final_pass_rate'] < 90
            ):
                item['quality_level'] = 'danger'
                item['quality_label'] = '高风险'
            elif item['warning_count'] or (
                    item['final_pass_rate'] is not None and item['final_pass_rate'] < 98
            ):
                item['quality_level'] = 'warning'
                item['quality_label'] = '需关注'
            else:
                item['quality_level'] = 'success'
                item['quality_label'] = '稳定'
        return current_items[:100]

    @classmethod
    def _scene_matrix(cls, suites, details) -> dict:
        grouped = defaultdict(list)
        for item in details.values(
                'test_suite__test_env',
                'test_suite__execution_scenes',
                'case_sum',
                'status',
                'success',
                'fail',
                'warning',
        ):
            for scene in item['test_suite__execution_scenes'] or []:
                grouped[(item['test_suite__test_env'], scene)].append(item)
        matrix = defaultdict(dict)
        for (env, scene), rows in grouped.items():
            counts = TestSuiteSummaryService.execution_status_counts_from_rows(rows)
            completed = TestSuiteSummaryService.completed_execution_count(counts)
            matrix[str(env)][scene] = {
                'detail_count': sum(counts.values()),
                'final_pass_rate': cls._rate(counts['success'], completed),
                'failed_count': counts['fail'],
            }
        scene_options = [
            {'key': item.value, 'title': AutomationExecutionSceneEnum.get_value(item.value)}
            for item in AutomationExecutionSceneEnum
            if item != AutomationExecutionSceneEnum.UNCLASSIFIED
        ]
        environment_options = [
            {'key': env.value, 'title': EnvironmentEnum.get_value(env.value)}
            for env in EnvironmentEnum
            if str(env.value) in matrix
        ]
        return {
            'scenes': scene_options,
            'environments': environment_options,
            'values': matrix,
        }

    @classmethod
    def _automation_type_quality(cls, details, executions) -> list[dict]:
        rows = list(details.values(
            'id',
            'test_suite_id',
            'test_suite__tasks_id',
            'test_suite__create_time',
            'type',
            'case_id',
            'case_sum',
            'status',
            'success',
            'fail',
            'warning',
        ))
        if not rows:
            return []

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
        recovered_ids = first_failed_ids & latest_success_ids
        result = []
        for case_type in TestCaseTypeEnum:
            type_rows = [item for item in rows if item['type'] == case_type.value]
            if not type_rows:
                continue
            counts = TestSuiteSummaryService.execution_status_counts_from_rows(type_rows)
            completed = TestSuiteSummaryService.completed_execution_count(counts)
            result.append({
                'type': case_type.value,
                'type_name': TestCaseTypeEnum.get_value(case_type.value),
                'execution_count': sum(counts.values()),
                'unique_case_count': TestSuiteSummaryService.unique_case_count_from_rows(
                    type_rows
                ),
                'success_count': counts['success'],
                'failed_count': counts['fail'],
                'warning_count': counts['warning'],
                'unfinished_count': counts['proceed'] + counts['stay_begin'],
                'final_pass_rate': cls._rate(counts['success'], completed),
                'retry_recovered_count': sum(
                    TestSuiteSummaryService.effective_case_sum(item)
                    for item in type_rows
                    if item['id'] in recovered_ids
                ),
            })
        return result
