from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from django.db.backends.sqlite3.base import DatabaseWrapper
from django.db.models.query import QuerySet
from mangotools.enums import TaskEnum

from src.apps.auto_api.models import ApiCase, ApiCaseDetailedParameter
from src.apps.auto_pytest.models import PytestCase
from src.apps.auto_ui.models import UiCase
from src.apps.test_center.api.views.index import IndexViews
from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.models import TestSuiteDetails
from src.apps.test_center.selectors.statistics import ReportStatisticsSelector
from src.apps.test_center.services.reporting.api_counting import ApiReportCountingService as Counting
from src.apps.test_center.services.reporting.test_suite.summary import TestSuiteSummaryService as Summary


class HomeApiCountingTests(SimpleTestCase):
    def rows(self):
        return [
            {'type': TestCaseTypeEnum.API.value, 'case_sum': 4, 'status': TaskEnum.FAIL.value,
             'success': 3, 'fail': 1, 'warning': 0, 'create_time': datetime(2026, 11, 16)},
            {'type': TestCaseTypeEnum.API.value, 'case_sum': 4, 'status': TaskEnum.SUCCESS.value,
             'success': 4, 'fail': 0, 'warning': 0, 'create_time': datetime(2026, 11, 16)},
            {'type': TestCaseTypeEnum.UI.value, 'case_sum': 2, 'status': TaskEnum.SUCCESS.value,
             'success': 2, 'fail': 0, 'warning': 0, 'create_time': datetime(2026, 11, 16)},
        ]

    def test_history_projection_changes_totals_and_rates_without_mutating_report_rows(self):
        original = self.rows()
        scenes = Summary.execution_status_counts_from_rows(Counting.statistics_rows(original, True))
        cases = Summary.execution_status_counts_from_rows(Counting.statistics_rows(original, False))
        self.assertEqual((sum(scenes.values()), scenes['success'], scenes['fail']), (10, 9, 1))
        self.assertEqual((sum(cases.values()), cases['success'], cases['fail']), (4, 3, 1))
        self.assertEqual(original[0]['case_sum'], 4)
        self.assertEqual(original[0]['success'], 3)

    def test_case_report_can_expand_back_to_scenes_from_small_counter_snapshot(self):
        row = {**self.rows()[0], 'case_sum': 1, 'success': 0, 'fail': 1,
               'statistics_api_mode': False, 'statistics_scene_count': 4,
               'statistics_scene_counter': {'success': 3, 'fail': 1, 'warning': 0}}
        projected = next(Counting.statistics_rows([row], True))
        self.assertEqual((projected['case_sum'], projected['success'], projected['fail']), (4, 3, 1))

    def test_legacy_case_report_expands_from_summary_only_and_missing_evidence_does_not_invent_scenes(self):
        row = {**self.rows()[0], 'case_sum': 1, 'statistics_api_mode': False,
               'statistics_legacy_children': [{'status': 1}] * 3 + [{'status': 0}]}
        projected = next(Counting.statistics_rows([row], True))
        self.assertEqual((projected['case_sum'], projected['success'], projected['fail']), (4, 3, 1))
        row['statistics_legacy_children'] = None
        self.assertEqual(next(Counting.statistics_rows([row], True))['case_sum'], 1)
        row.update(status=TaskEnum.SUCCESS.value, success=1, fail=0)
        projected = next(Counting.statistics_rows([row], True))
        self.assertEqual((projected['case_sum'], projected['success'], projected['fail']), (1, 1, 0))

    def test_case_mode_does_not_count_partial_success_as_a_completed_case(self):
        for status, expected in ((TaskEnum.PROCEED.value, 'proceed'), (TaskEnum.STAY_BEGIN.value, 'stay_begin'),
                                 (TaskEnum.INFRASTRUCTURE_BLOCKED.value, 'blocked')):
            row = {**self.rows()[0], 'status': status, 'fail': 0}
            counts = Summary.execution_status_counts_from_rows(Counting.statistics_rows([row], False))
            self.assertEqual(counts[expected], 1)
            self.assertEqual(counts['success'], 0)

    def test_selector_streams_counts_without_result_files_or_full_summary_json(self):
        captured = []
        with patch.object(QuerySet, 'iterator', autospec=True, side_effect=lambda qs, **kwargs: captured.append((qs, kwargs)) or iter(())):
            list(ReportStatisticsSelector.rows(TestSuiteDetails.objects.all(), ('type', 'case_sum'), True))
        qs, options = captured[0]
        self.assertEqual(options['chunk_size'], 2000)
        self.assertNotIn('summary_data', qs.query.values_select)
        connection = DatabaseWrapper({'NAME': ':memory:'}, alias='statistics-compile-only')
        sql, params = qs.query.get_compiler(connection=connection).as_sql()
        self.assertIn('CASE WHEN', sql)
        self.assertTrue(any('api_scene_counter' in str(value) for value in params))

    def test_weekly_and_seven_day_endpoints_use_current_mode_and_separate_cached_results(self):
        request = SimpleNamespace(user=SimpleNamespace(user_obj=SimpleNamespace(id=7)))
        cached = {}
        mode = {'value': False}
        with patch('src.apps.system.services.configuration.system_config.SystemConfigService.get', side_effect=lambda *a, **kw: mode['value']), \
                patch('src.apps.system.services.configuration.system_config.SystemConfigService.get_ranged_int', return_value=60), \
                patch.object(IndexViews, '_allowed_product_ids', return_value=None), \
                patch.object(IndexViews, '_current_date', return_value=date(2026, 11, 16)), \
                patch.object(ReportStatisticsSelector, 'rows', side_effect=lambda *a: iter(self.rows())), \
                patch('src.apps.test_center.api.views.index.cache.get', side_effect=cached.get), \
                patch('src.apps.test_center.api.views.index.cache.set', side_effect=lambda key, value, timeout: cached.update({key: value})):
            cases = IndexViews().case_result_week_sum(request).data['data']
            self.assertEqual((sum(cases['api_count']), cases['api_label']), (2, 'API 用例'))
            counts = IndexViews().case_run_sum(request).data['data']
            self.assertEqual((counts['total'], counts['final_pass_rate']), (4, 75.0))
            mode['value'] = True
            scenes = IndexViews().case_result_week_sum(request).data['data']
            self.assertEqual((sum(scenes['api_count']), scenes['api_label']), (8, 'API 场景'))
            counts = IndexViews().case_run_sum(request).data['data']
            self.assertEqual((counts['total'], counts['final_pass_rate']), (10, 90.0))
            self.assertEqual(len(cached), 4)

    def test_asset_pie_uses_case_table_when_disabled_and_scenario_table_when_enabled(self):
        request = SimpleNamespace()
        values = {UiCase: 2, PytestCase: 3, ApiCase: 5, ApiCaseDetailedParameter: 20}
        for mode, expected, label in ((False, 5, 'API 用例'), (True, 20, 'API 场景')):
            with self.subTest(mode=mode), \
                    patch('src.apps.system.services.configuration.system_config.SystemConfigService.get', return_value=mode), \
                    patch.object(IndexViews, '_filter_project_product_queryset', side_effect=lambda req, qs, *args: SimpleNamespace(count=lambda: values[qs.model])), \
                    patch.object(IndexViews, '_cached_success', side_effect=lambda req, key, msg, builder: builder()):
                result = IndexViews().case_sum(request)
                self.assertEqual(result[1], {'value': expected, 'name': label})
