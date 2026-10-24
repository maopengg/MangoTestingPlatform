from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from hashlib import sha256

from django.core.cache import cache
from mangotools.enums import TaskEnum

from src.apps.test_center.models import ExecutionResult, TestSuiteDetails
from src.apps.test_center.services.test_suite.summary import TestSuiteSummaryService

logger = logging.getLogger(__name__)


class AutomationEffectivenessOverviewMixin:
    @classmethod
    def _build_overview(cls, request) -> dict:
        suites, start_at, end_at = cls._suite_queryset(request)
        suite_ids = suites.values('id')
        details = TestSuiteDetails.objects.filter(test_suite_id__in=suite_ids)
        executions = ExecutionResult.objects.filter(test_suite_detail_id__in=details.values('id'))

        (
            previous_period,
            two_periods_ago_period,
            three_periods_ago_period,
        ) = cls._comparison_periods(start_at, end_at)
        previous_start_at, previous_end_at = previous_period
        previous_suites = cls._filtered_suite_queryset(
            request,
            previous_start_at,
            previous_end_at,
        )
        previous_details = TestSuiteDetails.objects.filter(
            test_suite_id__in=previous_suites.values('id')
        )
        previous_executions = ExecutionResult.objects.filter(
            test_suite_detail_id__in=previous_details.values('id')
        )

        two_periods_ago_start_at, two_periods_ago_end_at = two_periods_ago_period
        two_periods_ago_suites = cls._filtered_suite_queryset(
            request,
            two_periods_ago_start_at,
            two_periods_ago_end_at,
        )
        two_periods_ago_details = TestSuiteDetails.objects.filter(
            test_suite_id__in=two_periods_ago_suites.values('id')
        )
        two_periods_ago_executions = ExecutionResult.objects.filter(
            test_suite_detail_id__in=two_periods_ago_details.values('id')
        )

        three_periods_ago_start_at, three_periods_ago_end_at = three_periods_ago_period
        three_periods_ago_suites = cls._filtered_suite_queryset(
            request,
            three_periods_ago_start_at,
            three_periods_ago_end_at,
        )
        three_periods_ago_details = TestSuiteDetails.objects.filter(
            test_suite_id__in=three_periods_ago_suites.values('id')
        )
        three_periods_ago_executions = ExecutionResult.objects.filter(
            test_suite_detail_id__in=three_periods_ago_details.values('id')
        )

        cards = cls._summary_cards(suites, details, executions)
        previous_cards = cls._summary_cards(
            previous_suites,
            previous_details,
            previous_executions,
        )
        two_periods_ago_cards = cls._summary_cards(
            two_periods_ago_suites,
            two_periods_ago_details,
            two_periods_ago_executions,
        )
        three_periods_ago_cards = cls._summary_cards(
            three_periods_ago_suites,
            three_periods_ago_details,
            three_periods_ago_executions,
        )
        environment_quality = cls._environment_quality(suites, details, executions)
        inspection_tasks = cls._inspection_tasks(suites, details)
        module_quality = cls._module_quality(details, previous_details)
        module_risks = [
            item for item in module_quality
            if item['failed_count'] or item['warning_count']
        ]
        convergence = cls._convergence(details, previous_details)
        task_health = cls._task_health(suites, details)
        task_source_summary = cls._task_source_summary(task_health)
        failed_case_ranking = cls._failed_case_ranking(details)
        return {
            'period': {
                'start': cls._format_datetime(start_at),
                'end': cls._format_datetime(end_at - timedelta(microseconds=1)),
            },
            'previous_period': {
                'start': cls._format_datetime(previous_start_at),
                'end': cls._format_datetime(previous_end_at - timedelta(microseconds=1)),
            },
            'two_periods_ago_period': {
                'start': cls._format_datetime(two_periods_ago_start_at),
                'end': cls._format_datetime(
                    two_periods_ago_end_at - timedelta(microseconds=1)
                ),
            },
            'three_periods_ago_period': {
                'start': cls._format_datetime(three_periods_ago_start_at),
                'end': cls._format_datetime(
                    three_periods_ago_end_at - timedelta(microseconds=1)
                ),
            },
            'cards': cards,
            'comparison': cls._comparison(cards, previous_cards, convergence),
            'period_quality': [
                cls._period_quality_item(
                    'three_periods_ago',
                    '上上上周期',
                    three_periods_ago_start_at,
                    three_periods_ago_end_at,
                    three_periods_ago_cards,
                ),
                cls._period_quality_item(
                    'two_periods_ago',
                    '上上周期',
                    two_periods_ago_start_at,
                    two_periods_ago_end_at,
                    two_periods_ago_cards,
                ),
                cls._period_quality_item(
                    'previous',
                    '上一周期',
                    previous_start_at,
                    previous_end_at,
                    previous_cards,
                ),
                cls._period_quality_item(
                    'current',
                    '本周期',
                    start_at,
                    end_at,
                    cards,
                ),
            ],
            'benefits': cls._benefits(suites, details, executions, cards, convergence),
            'insights': cls._insights(
                cards,
                environment_quality,
                inspection_tasks,
                module_risks,
            ),
            'trend': cls._trend(details, start_at, end_at),
            'status_distribution': cls._status_distribution(details),
            'scene_distribution': cls._scene_distribution(details),
            'scope_distribution': cls._scope_distribution(details),
            'environment_quality': environment_quality,
            'scene_matrix': cls._scene_matrix(suites, details),
            'automation_type_quality': cls._automation_type_quality(details, executions),
            'task_source_summary': task_source_summary,
            'task_health': task_health,
            'failed_case_ranking': failed_case_ranking,
            'module_quality': module_quality,
            'module_risks': module_risks,
            'convergence': convergence,
            'inspection_tasks': inspection_tasks,
        }

    @classmethod
    def _summary_cards(cls, suites, details, executions) -> dict:
        detail_rows = list(details.values(
            'id', 'case_sum', 'status', 'success', 'fail', 'warning'
        ))
        status_counts = TestSuiteSummaryService.execution_status_counts_from_rows(
            detail_rows
        )
        detail_total = sum(status_counts.values())
        completed = (
                status_counts['success']
                + status_counts['fail']
                + status_counts['warning']
                + status_counts['stopped']
        )
        final_success = status_counts['success']
        failed_count = status_counts['fail']
        warning_count = status_counts['warning']
        first_recorded_ids = set(executions.filter(
            attempt_no=1
        ).values_list('test_suite_detail_id', flat=True).distinct())
        first_recorded_count = sum(
            TestSuiteSummaryService.effective_case_sum(item)
            for item in detail_rows
            if item['id'] in first_recorded_ids
        )
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
        flaky_count = sum(
            TestSuiteSummaryService.effective_case_sum(item)
            for item in detail_rows
            if item['id'] in recovered_ids
        )
        feedback = cls._first_feedback_metrics(suites, details, executions)
        return {
            'suite_count': suites.count(),
            'detail_count': detail_total,
            'final_pass_rate': cls._rate(final_success, completed),
            'completion_rate': cls._rate(completed, detail_total),
            'flaky_rate': cls._rate(flaky_count, first_recorded_count),
            'flaky_count': flaky_count,
            'success_count': final_success,
            'failed_count': failed_count,
            'warning_count': warning_count,
            'proceed_count': status_counts['proceed'],
            'stay_begin_count': status_counts['stay_begin'],
            'stopped_count': status_counts['stopped'],
            'issue_count': failed_count + warning_count,
            'unfinished_count': status_counts['proceed'] + status_counts['stay_begin'],
            'p95_first_feedback_seconds': feedback['p95_seconds'],
            'p95_feedback_seconds': feedback['p95_seconds'],
            'feedback_sample_count': feedback['sample_count'],
            'feedback_report_count': feedback['report_count'],
            'feedback_sample_coverage': feedback['sample_coverage'],
            'data_completeness': cls._rate(first_recorded_count, detail_total),
        }

    @classmethod
    def _period_quality_item(
            cls,
            key: str,
            label: str,
            start_at: datetime,
            end_at: datetime,
            cards: dict,
    ) -> dict:
        return {
            'key': key,
            'label': label,
            'start': cls._format_datetime(start_at),
            'end': cls._format_datetime(end_at - timedelta(microseconds=1)),
            'suite_count': cards.get('suite_count', 0),
            'detail_count': cards.get('detail_count', 0),
            'success_count': cards.get('success_count', 0),
            'failed_count': cards.get('failed_count', 0),
            'warning_count': cards.get('warning_count', 0),
            'proceed_count': cards.get('proceed_count', 0),
            'stay_begin_count': cards.get('stay_begin_count', 0),
            'stopped_count': cards.get('stopped_count', 0),
            'unfinished_count': cards.get('unfinished_count', 0),
            'final_pass_rate': cards.get('final_pass_rate'),
            'completion_rate': cards.get('completion_rate'),
        }

    @classmethod
    def _cache_key(cls, request) -> str:
        filters = {}
        for key in cls.CACHE_FILTER_KEYS:
            if key in cls.MULTI_FILTER_KEYS:
                values = sorted(cls._query_values(request, key))
                if values:
                    filters[key] = values
                continue
            value = request.query_params.get(key)
            if value not in (None, ''):
                filters[key] = value
        payload = json.dumps(filters, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
        filter_digest = sha256(payload.encode('utf-8')).hexdigest()[:24]
        generation = cache.get(cls._generation_key(request)) or '1'
        return f'{cls.CACHE_PREFIX}:generation:{generation}:filters:{filter_digest}'

    @classmethod
    def _generation_key(cls, request) -> str:
        scope_digest = sha256(cls._permission_scope(request).encode('utf-8')).hexdigest()[:24]
        return f'{cls.CACHE_PREFIX}:scope:{scope_digest}:generation'
