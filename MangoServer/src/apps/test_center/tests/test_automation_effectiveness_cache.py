from datetime import date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.db.models import Q
from django.http import QueryDict
from django.test import SimpleTestCase, override_settings

from src.apps.system.exceptions import ai_service_error
from src.apps.test_center.api.views.index import IndexViews
from src.apps.test_center.services.reporting.test_suite.effectiveness import AutomationEffectivenessService
from src.apps.test_center.services.reporting.test_suite.summary import TestSuiteSummaryService


@override_settings(CACHES={
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'automation-effectiveness-tests',
    }
})
class AutomationEffectivenessCacheTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    @staticmethod
    def request(**query_params):
        return SimpleNamespace(query_params=query_params, user=None)

    @patch('src.apps.test_center.services.reporting.test_suite.effectiveness.Tasks.objects')
    def test_cached_task_health_refreshes_diagnostic_file_path(self, task_manager):
        task_manager.filter.return_value.values_list.return_value = [
            (23, 'diagnostics/task-23.md'),
        ]
        data = {
            'task_health': [
                {'task_id': '23', 'diagnostic_file_path': None},
                {'task_id': 24, 'diagnostic_file_path': 'stale.md'},
            ],
        }

        result = AutomationEffectivenessService._refresh_task_diagnostic_paths(data)

        self.assertEqual(
            result['task_health'][0]['diagnostic_file_path'],
            'diagnostics/task-23.md',
        )
        self.assertIsNone(result['task_health'][1]['diagnostic_file_path'])
        task_manager.filter.assert_called_once_with(id__in={23, 24})

    def test_unique_case_count_uses_report_case_sum_snapshot(self):
        queryset = MagicMock()
        queryset.values.return_value = [
            {'type': 1, 'case_id': 101, 'case_sum': 4},
            {'type': 0, 'case_id': 201, 'case_sum': 1},
            {'type': 2, 'case_id': 301, 'case_sum': 2},
            {'type': 2, 'case_id': 401, 'case_sum': 0},
        ]

        count = TestSuiteSummaryService.unique_case_count(queryset)

        self.assertEqual(count, 8)

    def test_unique_case_count_does_not_repeat_the_same_case(self):
        count = TestSuiteSummaryService.unique_case_count_from_rows([
            {'type': 1, 'case_id': 101, 'case_sum': 3},
            {'type': 1, 'case_id': 101, 'case_sum': 3},
            {'type': 0, 'case_id': 201, 'case_sum': 1},
        ])

        self.assertEqual(count, 4)

    def test_report_snapshot_case_count_sums_all_scenarios_in_latest_task_report(self):
        count = TestSuiteSummaryService.unique_case_count_from_rows([
            {
                'test_suite_id': 1001,
                'test_suite__tasks_id': 8,
                'test_suite__create_time': datetime(2026, 8, 18, 22, 0),
                'type': 1,
                'case_id': 47,
                'case_sum': 2,
            },
            {
                'test_suite_id': 1001,
                'test_suite__tasks_id': 8,
                'test_suite__create_time': datetime(2026, 8, 18, 22, 0),
                'type': 1,
                'case_id': 47,
                'case_sum': 3,
            },
            {
                'test_suite_id': 1002,
                'test_suite__tasks_id': 8,
                'test_suite__create_time': datetime(2026, 8, 19, 22, 0),
                'type': 1,
                'case_id': 47,
                'case_sum': 4,
            },
            {
                'test_suite_id': 1002,
                'test_suite__tasks_id': 8,
                'test_suite__create_time': datetime(2026, 8, 19, 22, 0),
                'type': 1,
                'case_id': 47,
                'case_sum': 2,
            },
        ])

        self.assertEqual(count, 6)

    def test_execution_status_counts_use_case_sum_and_partial_progress(self):
        counts = TestSuiteSummaryService.execution_status_counts_from_rows([
            {
                'status': 1,
                'case_sum': 4,
                'success': 4,
                'fail': 0,
                'warning': 0,
            },
            {
                'status': 3,
                'case_sum': 5,
                'success': 2,
                'fail': 0,
                'warning': 0,
            },
            {
                'status': 0,
                'case_sum': 0,
                'success': 0,
                'fail': 0,
                'warning': 0,
            },
        ])

        self.assertEqual(counts['success'], 6)
        self.assertEqual(counts['proceed'], 3)
        self.assertEqual(counts['fail'], 1)
        self.assertEqual(sum(counts.values()), 10)

    def test_report_counter_uses_same_total_for_historical_zero_case_sum(self):
        counter = TestSuiteSummaryService.counter_data_from_rows([
            {
                'type': 0,
                'status': 1,
                'case_sum': 216,
                'success': 216,
                'fail': 0,
                'warning': 0,
            },
            {
                'type': 0,
                'status': 1,
                'case_sum': 0,
                'success': 1,
                'fail': 0,
                'warning': 0,
            },
        ])

        self.assertEqual(counter['case_sum'], 217)
        self.assertEqual(counter['success'], 217)
        self.assertEqual(counter['ui_case_sum'], 217)
        self.assertEqual(sum(counter[key] for key in [
            'success', 'fail', 'warning', 'proceed', 'stay_begin', 'stopped'
        ]), counter['case_sum'])

    def test_effectiveness_cards_use_case_sum_instead_of_detail_rows(self):
        details = MagicMock()
        details.values.return_value = [
            {
                'id': 1001,
                'case_sum': 4,
                'status': 1,
                'success': 4,
                'fail': 0,
                'warning': 0,
            },
            {
                'id': 1002,
                'case_sum': 2,
                'status': 0,
                'success': 0,
                'fail': 2,
                'warning': 0,
            },
        ]
        empty_execution_query = MagicMock()
        empty_execution_query.values_list.return_value.distinct.return_value = []
        executions = MagicMock()
        executions.filter.return_value = empty_execution_query
        suites = MagicMock()
        suites.count.return_value = 1

        with patch.object(
                AutomationEffectivenessService,
                '_first_feedback_metrics',
                return_value={
                    'p95_seconds': None,
                    'sample_count': 0,
                    'report_count': 1,
                    'sample_coverage': 0.0,
                },
        ):
            result = AutomationEffectivenessService._summary_cards(
                suites, details, executions
            )

        self.assertEqual(result['detail_count'], 6)
        self.assertEqual(result['failed_count'], 2)
        self.assertEqual(result['final_pass_rate'], 66.67)
        self.assertEqual(result['completion_rate'], 100.0)

    def test_first_feedback_metrics_only_include_complete_first_attempt_reports(self):
        created_at = datetime(2026, 8, 20, 10, 0, 0)

        result = AutomationEffectivenessService._first_feedback_metrics_from_rows(
            [
                {'id': 1, 'create_time': created_at},
                {'id': 2, 'create_time': created_at},
            ],
            [
                {'id': 101, 'test_suite_id': 1},
                {'id': 102, 'test_suite_id': 1},
                {'id': 201, 'test_suite_id': 2},
            ],
            [
                {
                    'test_suite_detail_id': 101,
                    'test_suite_detail__test_suite_id': 1,
                    'first_result_at': created_at + timedelta(minutes=5),
                },
                {
                    'test_suite_detail_id': 102,
                    'test_suite_detail__test_suite_id': 1,
                    'first_result_at': created_at + timedelta(minutes=8),
                },
            ],
        )

        self.assertEqual(result['p95_seconds'], 480.0)
        self.assertEqual(result['sample_count'], 1)
        self.assertEqual(result['report_count'], 2)
        self.assertEqual(result['sample_coverage'], 50.0)

    def test_period_quality_item_keeps_equal_period_dates_and_case_sum_metrics(self):
        item = AutomationEffectivenessService._period_quality_item(
            'previous',
            '上一周期',
            datetime(2026, 8, 4),
            datetime(2026, 8, 11),
            {
                'suite_count': 2,
                'detail_count': 613,
                'success_count': 600,
                'failed_count': 8,
                'warning_count': 5,
                'proceed_count': 3,
                'stay_begin_count': 2,
                'stopped_count': 0,
                'unfinished_count': 0,
                'final_pass_rate': 97.88,
                'completion_rate': 100.0,
            },
        )

        self.assertEqual(item['key'], 'previous')
        self.assertEqual(item['start'], '2026-08-04 00:00:00')
        self.assertEqual(item['end'], '2026-08-10 23:59:59')
        self.assertEqual(item['detail_count'], 613)
        self.assertEqual(item['success_count'], 600)
        self.assertEqual(item['proceed_count'], 3)
        self.assertEqual(item['stay_begin_count'], 2)
        self.assertEqual(item['final_pass_rate'], 97.88)

    def test_comparison_periods_follow_the_selected_period_length(self):
        for period_days in (7, 10, 31):
            start_at = datetime(2026, 8, 21)
            end_at = start_at + timedelta(days=period_days)

            (
                previous,
                two_periods_ago,
                three_periods_ago,
            ) = AutomationEffectivenessService._comparison_periods(start_at, end_at)

            self.assertEqual(previous[1] - previous[0], timedelta(days=period_days))
            self.assertEqual(two_periods_ago[1] - two_periods_ago[0], timedelta(days=period_days))
            self.assertEqual(three_periods_ago[1] - three_periods_ago[0], timedelta(days=period_days))
            self.assertEqual(previous[1], start_at)
            self.assertEqual(two_periods_ago[1], previous[0])
            self.assertEqual(three_periods_ago[1], two_periods_ago[0])

    def test_scene_matrix_uses_case_sum_instead_of_detail_rows(self):
        details = MagicMock()
        details.values.return_value = [
            {
                'test_suite__test_env': 1,
                'test_suite__execution_scenes': ['routine_regression'],
                'case_sum': 4,
                'status': 1,
                'success': 4,
                'fail': 0,
                'warning': 0,
            },
            {
                'test_suite__test_env': 1,
                'test_suite__execution_scenes': ['routine_regression'],
                'case_sum': 2,
                'status': 0,
                'success': 0,
                'fail': 2,
                'warning': 0,
            },
        ]

        result = AutomationEffectivenessService._scene_matrix(MagicMock(), details)
        row = result['values']['1']['routine_regression']

        self.assertEqual(row['detail_count'], 6)
        self.assertEqual(row['failed_count'], 2)
        self.assertEqual(row['final_pass_rate'], 66.67)

    def test_task_source_summary_exposes_auditable_source_totals(self):
        result = AutomationEffectivenessService._task_source_summary([
            {
                'suite_count': 3,
                'execution_count': 120,
                'report_success_count': 2,
            },
            {
                'suite_count': 1,
                'execution_count': 30,
                'report_success_count': 1,
            },
        ])

        self.assertEqual(result['task_count'], 2)
        self.assertEqual(result['report_count'], 4)
        self.assertEqual(result['execution_count'], 150)
        self.assertEqual(result['report_success_count'], 3)

    def test_benefits_use_unified_case_counts_and_split_task_scenes(self):
        suites = MagicMock()
        suites.values.return_value = [
            {
                'execution_scenes': ['routine_regression'],
                'project_product_id': 1,
                'module_id': 11,
                'test_env': 1,
                'create_time': datetime(2026, 8, 18, 9, 0, 0),
            },
            {
                'execution_scenes': ['stability_monitoring'],
                'project_product_id': 1,
                'module_id': None,
                'test_env': 2,
                'create_time': datetime(2026, 8, 19, 9, 0, 0),
            },
        ]
        details = MagicMock()
        details.values.return_value = [
            {
                'id': 1001,
                'test_suite__execution_scenes': ['routine_regression'],
                'type': 1,
                'case_id': 101,
                'case_sum': 4,
                'status': 1,
                'success': 4,
                'fail': 0,
                'warning': 0,
            },
            {
                'id': 1002,
                'test_suite__execution_scenes': ['stability_monitoring'],
                'type': 0,
                'case_id': 201,
                'case_sum': 2,
                'status': 0,
                'success': 0,
                'fail': 2,
                'warning': 0,
            },
        ]
        failed_executions = MagicMock()
        failed_executions.values_list.return_value.distinct.return_value = []
        success_executions = MagicMock()
        success_executions.values_list.return_value.distinct.return_value = []
        executions = MagicMock()
        executions.filter.side_effect = [failed_executions, success_executions]

        result = AutomationEffectivenessService._benefits(
            suites,
            details,
            executions,
            {
                'suite_count': 2,
                'flaky_count': 0,
                'p95_first_feedback_seconds': 18.5,
                'p95_feedback_seconds': 18.5,
                'feedback_sample_count': 2,
                'feedback_report_count': 2,
                'feedback_sample_coverage': 100.0,
            },
            {'affected_case_count': 1, 'recovered_case_count': 0},
        )

        self.assertEqual(result['execution_count'], 6)
        self.assertEqual(result['unique_case_count'], 6)
        self.assertEqual(result['abnormal_result_count'], 2)
        self.assertEqual(result['active_day_count'], 2)
        self.assertEqual(result['module_count'], 1)
        self.assertEqual(result['environment_count'], 2)
        scene_map = {item['scene']: item for item in result['scene_benefits']}
        self.assertEqual(scene_map['routine_regression']['execution_count'], 4)
        self.assertEqual(scene_map['stability_monitoring']['abnormal_count'], 2)

    def test_index_date_helpers_support_naive_datetime(self):
        current = datetime(2026, 8, 20, 10, 3, 52)
        with patch('src.apps.test_center.api.views.index.timezone.now', return_value=current):
            self.assertEqual(IndexViews._current_date(), date(2026, 8, 20))
            day_start = IndexViews._day_start(date(2026, 8, 14))

        self.assertEqual(day_start, datetime(2026, 8, 14, 0, 0, 0))
        self.assertIsNone(day_start.tzinfo)

    def test_same_filters_reuse_cached_overview(self):
        request = self.request(test_env='2', execution_scene='stability_monitoring')
        with (
            patch.object(
                AutomationEffectivenessService,
                '_build_overview',
                return_value={'cards': {'suite_count': 3}},
            ) as build_overview,
            patch.object(cache, 'set', wraps=cache.set) as cache_set,
        ):
            first = AutomationEffectivenessService.overview(request)
            second = AutomationEffectivenessService.overview(request)

        self.assertEqual(first, second)
        build_overview.assert_called_once_with(request)
        self.assertEqual(cache_set.call_args.args[2], 60 * 10)

    def test_clear_cache_invalidates_all_filters_for_current_scope(self):
        request = self.request(test_env='2')
        with patch.object(
                AutomationEffectivenessService,
                '_build_overview',
                side_effect=[{'version': 1}, {'version': 2}],
        ) as build_overview:
            self.assertEqual(AutomationEffectivenessService.overview(request), {'version': 1})
            AutomationEffectivenessService.clear_cache(request)
            self.assertEqual(AutomationEffectivenessService.overview(request), {'version': 2})

        self.assertEqual(build_overview.call_count, 2)

    def test_different_filters_do_not_share_cache(self):
        with patch.object(
                AutomationEffectivenessService,
                '_build_overview',
                side_effect=[{'environment': 1}, {'environment': 2}],
        ) as build_overview:
            first = AutomationEffectivenessService.overview(self.request(project_id='1'))
            second = AutomationEffectivenessService.overview(self.request(project_id='2'))

        self.assertNotEqual(first, second)
        self.assertEqual(build_overview.call_count, 2)

    def test_multi_filters_accept_repeated_array_and_comma_separated_params(self):
        query_params = QueryDict('', mutable=True)
        query_params.setlist('test_env', ['1', '2'])
        query_params.setlist('execution_scene[]', ['routine_regression', 'production_inspection'])
        query_params['execution_scope'] = 'module,full_product'
        request = SimpleNamespace(query_params=query_params, user=None)

        self.assertEqual(
            AutomationEffectivenessService._query_values(request, 'test_env'),
            ['1', '2'],
        )
        self.assertEqual(
            AutomationEffectivenessService._query_values(request, 'execution_scene'),
            ['routine_regression', 'production_inspection'],
        )
        self.assertEqual(
            AutomationEffectivenessService._query_values(request, 'execution_scope'),
            ['module', 'full_product'],
        )

    def test_multi_filter_cache_key_is_independent_of_selection_order(self):
        first = self.request(test_env='1,2', execution_scope='module,full_product')
        second = self.request(test_env='2,1', execution_scope='full_product,module')

        self.assertEqual(
            AutomationEffectivenessService._cache_key(first),
            AutomationEffectivenessService._cache_key(second),
        )

    @patch('src.apps.test_center.services.reporting.test_suite.effectiveness.TestSuite.objects')
    def test_suite_queryset_applies_multi_value_filters(self, test_suite_manager):
        queryset = MagicMock()
        test_suite_manager.filter.return_value.select_related.return_value = queryset
        queryset.filter.return_value = queryset
        request = self.request(
            test_env='1,2',
            execution_scope='module,full_product',
            execution_scene='routine_regression,production_inspection',
        )

        AutomationEffectivenessService._filtered_suite_queryset(
            request,
            datetime(2026, 8, 1),
            datetime(2026, 8, 8),
        )

        queryset.filter.assert_any_call(test_env__in=['1', '2'])
        queryset.filter.assert_any_call(execution_scope__in=['module', 'full_product'])
        scene_call = next(
            call for call in queryset.filter.call_args_list if call.args and isinstance(call.args[0], Q)
        )
        self.assertEqual(scene_call.args[0].connector, Q.OR)
        self.assertEqual(len(scene_call.args[0].children), 2)

    def test_comparison_uses_previous_period_as_baseline(self):
        current = {
            'suite_count': 8,
            'detail_count': 120,
            'final_pass_rate': 97.5,
            'flaky_rate': 3.0,
            'issue_count': 6,
        }
        previous = {
            'suite_count': 6,
            'detail_count': 100,
            'final_pass_rate': 95.0,
            'flaky_rate': 5.0,
            'issue_count': 10,
        }
        comparison = AutomationEffectivenessService._comparison(
            current,
            previous,
            {'issue_rate_delta': -4.0},
        )

        self.assertTrue(comparison['has_previous'])
        self.assertEqual(comparison['final_pass_rate_delta'], 2.5)
        self.assertEqual(comparison['detail_count_delta'], 20)
        self.assertEqual(comparison['issue_count_delta'], -4)
        self.assertEqual(comparison['issue_rate_delta'], -4.0)

    def test_insights_explain_high_flaky_rate(self):
        insights = AutomationEffectivenessService._insights(
            {
                'suite_count': 44,
                'unfinished_count': 0,
                'flaky_rate': 2.48,
                'flaky_count': 308,
                'data_completeness': 100.0,
            },
            [],
            [],
            [],
        )

        self.assertEqual(insights[0]['level'], 'warning')
        self.assertIn('执行不稳定率 2.48%', insights[0]['title'])
        self.assertIn('308 个用例首轮失败后通过重试恢复', insights[0]['description'])

    def test_default_date_range_uses_seven_days(self):
        now = datetime(2026, 8, 19, 19, 30, 0)
        with patch(
                'src.apps.test_center.services.reporting.test_suite.effectiveness.timezone.now',
                return_value=now,
        ):
            start_at, end_at = AutomationEffectivenessService._date_range(self.request())

        self.assertEqual(end_at, now)
        self.assertEqual(start_at, now - timedelta(days=7))

    def test_custom_period_uses_adjacent_period_with_same_length(self):
        current_start = datetime(2026, 7, 26)
        current_end = datetime(2026, 8, 20)

        previous_start, previous_end = AutomationEffectivenessService._previous_period(
            current_start,
            current_end,
        )

        self.assertEqual(current_end - current_start, timedelta(days=25))
        self.assertEqual(previous_end - previous_start, timedelta(days=25))
        self.assertEqual(previous_end, current_start)

    def test_trend_includes_every_calendar_day_in_period(self):
        detail_rows = {
            date(2026, 8, 14): {
                'total': 18,
                'completed': 18,
                'success': 14,
                'failed': 3,
                'warning': 1,
            },
            date(2026, 8, 16): {
                'total': 18,
                'completed': 18,
                'success': 16,
                'failed': 1,
                'warning': 1,
            },
        }

        trend = AutomationEffectivenessService._complete_trend_days(
            detail_rows,
            datetime(2026, 8, 14),
            datetime(2026, 8, 21),
        )

        self.assertEqual([item['date'] for item in trend], [
            '08-14', '08-15', '08-16', '08-17', '08-18', '08-19', '08-20',
        ])
        self.assertEqual(trend[1]['detail_count'], 0)
        self.assertIsNone(trend[1]['final_pass_rate'])

    def test_comparison_without_previous_data_returns_no_delta(self):
        current = {
            'suite_count': 2,
            'detail_count': 20,
            'final_pass_rate': 95.0,
            'flaky_rate': 5.0,
            'issue_count': 1,
        }
        previous = {
            'suite_count': 0,
            'detail_count': 0,
            'final_pass_rate': None,
            'flaky_rate': None,
            'issue_count': 0,
        }
        comparison = AutomationEffectivenessService._comparison(
            current,
            previous,
            {'issue_rate_delta': None},
        )

        self.assertFalse(comparison['has_previous'])
        self.assertIsNone(comparison['final_pass_rate_delta'])
        self.assertIsNone(comparison['detail_count_delta'])

    def test_ai_summary_returns_unavailable_state_when_ai_is_not_configured(self):
        request = SimpleNamespace(
            query_params={},
            data={'overview': {'cards': {'suite_count': 3}}, 'context': {}},
            user=None,
        )
        with patch(
                'src.apps.test_center.services.reporting.test_suite.effectiveness.AiService.load_config',
                side_effect=ai_service_error('AI的APIKey未配置'),
        ):
            result = AutomationEffectivenessService.ai_summary(request)

        self.assertFalse(result['available'])
        self.assertEqual(result['setup_path'], '/system/settings/index')
        self.assertIn('APIKey', result['reason'])

    def test_ai_summary_normalizes_structured_result(self):
        request = SimpleNamespace(
            query_params={},
            data={'overview': {'cards': {'suite_count': 3}}, 'context': {}},
            user=None,
        )
        config = SimpleNamespace(model='test-model')
        ai_data = {
            'headline': '质量持续改善',
            'executive_summary': '最终通过率提升，问题数量下降，当前自动化收益可以被执行数据验证。',
            'quality_trend': {
                'status': 'improving',
                'label': '正在改善',
                'analysis': '最终通过率较上一周期提升。',
            },
            'benefits': [
                {
                    'title': '问题发现',
                    'detail': '发现异常',
                    'evidence': 'detected_issue_count=60, unique_case_count=18',
                },
            ],
            'risks': [],
            'recommendations': [],
            'chart_insights': {
                'trend': '失败次数下降，问题正在收敛。',
                'environment': '测试环境通过率最高。',
                'task_type': '冒烟验证质量表现最好。',
                'coverage_scope': '指定用例覆盖范围通过率最高。',
            },
            'component_insights': {
                'overview': '整体通过率有所提升，但仍有失败结果需要处理。',
                'status': '已完成结果占比较高，未完成用例仍需跟进。',
                'modules': '稳定模块数量较多，高风险模块应优先排查。',
                'benefits': '自动化覆盖持续增加，问题恢复效率仍可提升。',
            },
        }
        with (
            patch(
                'src.apps.test_center.services.reporting.test_suite.effectiveness.AiService.load_config',
                return_value=config,
            ),
            patch('src.apps.test_center.services.reporting.test_suite.effectiveness.AiService._validate_base_config'),
            patch(
                'src.apps.test_center.services.reporting.test_suite.effectiveness.AiService.json_chat',
                return_value={'choices': [{'message': {'content': '{}'}}]},
            ) as json_chat,
            patch(
                'src.apps.test_center.services.reporting.test_suite.effectiveness.extract_ai_json',
                return_value=ai_data,
            ),
        ):
            result = AutomationEffectivenessService.ai_summary(request)

        self.assertTrue(result['available'])
        self.assertEqual(result['model'], 'test-model')
        self.assertEqual(result['summary']['quality_trend']['status'], 'improving')
        self.assertEqual(result['summary']['benefits'][0]['title'], '问题发现')
        self.assertEqual(
            result['summary']['benefits'][0]['evidence'],
            '异常结果 60 次，覆盖 18 个用例',
        )
        self.assertEqual(
            result['summary']['chart_insights']['environment'],
            '测试环境通过率最高。',
        )
        self.assertEqual(
            result['summary']['component_insights']['modules'],
            '稳定模块数量较多，高风险模块应优先排查。',
        )
        self.assertEqual(
            json_chat.call_args.kwargs['thinking'],
            {'type': 'disabled'},
        )

    def test_ai_summary_reuses_one_hour_cache(self):
        request = SimpleNamespace(
            query_params={},
            data={'overview': {'cards': {'suite_count': 3}}, 'context': {}},
            user=None,
        )
        config = SimpleNamespace(model='test-model')
        ai_data = {
            'headline': '质量稳定',
            'executive_summary': '当前质量保持稳定。',
            'quality_trend': {
                'status': 'stable',
                'label': '保持稳定',
                'analysis': '当前周期没有明显波动。',
            },
            'benefits': [],
            'risks': [],
            'recommendations': [],
        }
        with (
            patch(
                'src.apps.test_center.services.reporting.test_suite.effectiveness.AiService.load_config',
                return_value=config,
            ),
            patch('src.apps.test_center.services.reporting.test_suite.effectiveness.AiService._validate_base_config'),
            patch(
                'src.apps.test_center.services.reporting.test_suite.effectiveness.AiService.json_chat',
                return_value={'choices': [{'message': {'content': '{}'}}]},
            ) as json_chat,
            patch(
                'src.apps.test_center.services.reporting.test_suite.effectiveness.extract_ai_json',
                return_value=ai_data,
            ),
            patch.object(cache, 'set', wraps=cache.set) as cache_set,
        ):
            first = AutomationEffectivenessService.ai_summary(request)
            second = AutomationEffectivenessService.ai_summary(request)

        self.assertEqual(first, second)
        json_chat.assert_called_once()
        self.assertEqual(cache_set.call_args.args[2], 60 * 60)

    def test_component_insight_uses_specific_prompt_and_one_hour_cache(self):
        request = SimpleNamespace(
            query_params={},
            data={
                'mode': 'insights',
                'overview': {
                    'benefits': {
                        'execution_count': 80,
                        'unique_case_count': 18,
                        'abnormal_result_count': 5,
                        'period_recovered_case_count': 3,
                    },
                    'comparison': {'issue_count_delta': -4},
                    'convergence': {'direction': 'converging'},
                },
                'context': {'period': '2026-08-14 至 2026-08-20'},
                'insight_keys': ['benefits'],
            },
            user=None,
        )
        config = SimpleNamespace(model='test-model')
        with (
            patch(
                'src.apps.test_center.services.reporting.test_suite.effectiveness.AiService.load_config',
                return_value=config,
            ),
            patch('src.apps.test_center.services.reporting.test_suite.effectiveness.AiService._validate_base_config'),
            patch(
                'src.apps.test_center.services.reporting.test_suite.effectiveness.AiService.json_chat',
                return_value={'choices': [{'message': {'content': '{}'}}]},
            ) as json_chat,
            patch(
                'src.apps.test_center.services.reporting.test_suite.effectiveness.extract_ai_json',
                return_value={
                    'insight': '自动化覆盖18个用例，问题率下降且3个用例恢复，收益可验证。',
                },
            ),
            patch.object(cache, 'set', wraps=cache.set) as cache_set,
        ):
            first = AutomationEffectivenessService.ai_summary(request)
            second = AutomationEffectivenessService.ai_summary(request)

        self.assertTrue(first['available'])
        self.assertEqual(
            second['insights']['benefits'],
            '自动化覆盖18个用例，问题率下降且3个用例恢复，收益可验证。',
        )
        json_chat.assert_called_once()
        prompt = json_chat.call_args.kwargs['messages'][0]['content']
        self.assertIn('自动化收益', prompt)
        self.assertIn('替代了多少重复回归', prompt)
        self.assertIn('不能把失败结果直接称为缺陷', prompt)
        self.assertEqual(cache_set.call_args.args[2], 60 * 60)

    def test_unassigned_task_module_is_grouped_under_all_modules(self):
        details = SimpleNamespace(values=lambda *fields: [
            {
                'type': 1,
                'case_id': 101,
                'status': 1,
                'test_suite_id': 1001,
                'test_suite__create_time': None,
                'test_suite__module_id': None,
                'test_suite__project_product_id': 8,
                'test_suite__project_product__name': '演示产品',
                'test_suite__project_product__project__name': '演示项目',
            },
            {
                'type': 1,
                'case_id': 102,
                'status': 1,
                'test_suite_id': 1001,
                'test_suite__create_time': None,
                'test_suite__module_id': None,
                'test_suite__project_product_id': 8,
                'test_suite__project_product__name': '演示产品',
                'test_suite__project_product__project__name': '演示项目',
            },
        ])
        with patch(
                'src.apps.test_center.services.reporting.test_suite.effectiveness.ProductModuleService.with_full_paths',
                return_value=[],
        ):
            result = AutomationEffectivenessService._aggregate_module_quality(details)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['module_key'], 'all:8')
        self.assertEqual(result[0]['module_path'], '全部模块')
        self.assertEqual(result[0]['execution_scope_name'], '全部模块')
        self.assertEqual(result[0]['case_count'], 2)

    def test_failed_case_ranking_includes_single_failures_and_sorts_by_count(self):
        values_result = MagicMock()
        values_result.order_by.return_value = [
            {
                'id': 4,
                'test_suite_id': 1004,
                'type': 1,
                'case_id': 101,
                'case_name': '持续失败用例',
                'status': 1,
                'error_message': None,
                'test_suite__tasks_id': 8,
                'test_suite__tasks__name': '生产巡检',
                'test_suite__project_product__name': '订单平台',
                'test_suite__test_env': 1,
                'test_suite__create_time': datetime(2026, 8, 20, 10, 0),
            },
            {
                'id': 3,
                'test_suite_id': 1003,
                'type': 1,
                'case_id': 101,
                'case_name': '持续失败用例',
                'status': 0,
                'error_message': '连接超时',
                'test_suite__tasks_id': 8,
                'test_suite__tasks__name': '生产巡检',
                'test_suite__project_product__name': '订单平台',
                'test_suite__test_env': 1,
                'test_suite__create_time': datetime(2026, 8, 19, 10, 0),
            },
            {
                'id': 2,
                'test_suite_id': 1002,
                'type': 1,
                'case_id': 101,
                'case_name': '持续失败用例',
                'status': 0,
                'error_message': '连接超时',
                'test_suite__tasks_id': 8,
                'test_suite__tasks__name': '生产巡检',
                'test_suite__project_product__name': '订单平台',
                'test_suite__test_env': 1,
                'test_suite__create_time': datetime(2026, 8, 18, 10, 0),
            },
            {
                'id': 1,
                'test_suite_id': 1001,
                'type': 1,
                'case_id': 102,
                'case_name': '偶发失败用例',
                'status': 0,
                'error_message': '断言失败',
                'test_suite__tasks_id': 8,
                'test_suite__tasks__name': '生产巡检',
                'test_suite__project_product__name': '订单平台',
                'test_suite__test_env': 1,
                'test_suite__create_time': datetime(2026, 8, 20, 10, 0),
            },
        ]
        details = MagicMock()
        details.values.return_value = values_result

        result = AutomationEffectivenessService._failed_case_ranking(details)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['case_id'], 101)
        self.assertEqual(result[0]['failed_count'], 2)
        self.assertEqual(result[0]['attempt_count'], 3)
        self.assertEqual(result[0]['latest_error'], '连接超时')
        self.assertEqual(result[0]['latest_failed_detail_id'], 3)
        self.assertEqual(result[0]['latest_failed_suite_id'], 1003)
        self.assertEqual(result[1]['case_id'], 102)
        self.assertEqual(result[1]['failed_count'], 1)
