from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from mangotools.enums import TaskEnum

from src.apps.system.services.configuration.system_config import SYSTEM_CONFIG_REGISTRY
from src.apps.task_center.services.execution.add_tasks import AddTasks
from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.models import TestSuite
from src.apps.test_center.services.reporting.api_counting import ApiReportCountingService as Counting
from src.apps.test_center.services.reporting.test_suite.create import TestSuiteCreateService
from src.apps.test_center.services.reporting.test_suite.detail_result import TestSuiteExecutionResultService as Results
from src.apps.test_center.services.reporting.test_suite.summary import TestSuiteSummaryService as Summary
from src.apps.test_center.services.reporting.testcounter import TestCounter
from src.apps.test_center.services.reporting.test_suite.retry import TestSuiteRetryService
from src.apps.test_center.services.reporting.test_suite.timeout_recovery import TestSuiteTimeoutRecoveryService


class ApiReportCountingTests(SimpleTestCase):
    def detail(self, by_scenario, status=TaskEnum.SUCCESS.value):
        return SimpleNamespace(id=1, type=TestCaseTypeEnum.API.value, status=status,
                               case_sum=4 if by_scenario else 1, success=0, fail=0, warning=0,
                               summary_data={'children': None, 'meta': {'api_count_by_scenario': by_scenario}})

    def test_registered_configuration_is_default_on_in_report_delivery(self):
        config = next(item for item in SYSTEM_CONFIG_REGISTRY if item.key == 'API_REPORT_COUNT_BY_SCENARIO')
        self.assertIs(config.default_value, True)
        self.assertEqual(config.group, 'report_delivery')
        self.assertIs(TestSuite._meta.get_field('api_count_by_scenario').default, True)

    def test_report_snapshots_configuration_once_at_creation(self):
        with patch('src.apps.test_center.services.reporting.test_suite.create.SystemConfigService.get', return_value=False) as config, \
                patch('src.apps.test_center.services.reporting.test_suite.create.TestSuite.objects.create',
                      side_effect=lambda **kwargs: SimpleNamespace(**kwargs)):
            suite = TestSuiteCreateService.create_suite(
                suite_id=1, project_product_id=1, module_id=None, test_env=0, execution_scenes=[],
                execution_scope='manual', user_id=1, status=TaskEnum.STAY_BEGIN.value, is_notice=0,
                task_id=None, execution_name='example', api_concurrency_limit=None,
            )
            config.return_value = True
            self.assertIs(suite.api_count_by_scenario, False)
            config.assert_called_once_with('API_REPORT_COUNT_BY_SCENARIO', default=True)

    def test_two_parameter_groups_times_four_scenarios_yields_eight_or_two(self):
        for mode, expected in ((True, 8), (False, 2)):
            add = AddTasks.__new__(AddTasks)
            add.test_suite_id, add.test_env, add.tasks_id, add.api_count_by_scenario = 1, 0, None, mode
            case = SimpleNamespace(id=9, name='example', project_product_id=7,
                                   parametrize=[{'name': 'one'}, {'name': 'two'}])
            with self.subTest(mode=mode), \
                    patch('src.apps.task_center.services.execution.add_tasks.ApiCase.objects.get', return_value=case), \
                    patch.object(TestCounter, 'case_api', return_value=4), \
                    patch('src.apps.test_center.services.reporting.test_suite.create.TestSuiteDetails.objects.create') as create:
                add.add_test_suite_details(9, TestCaseTypeEnum.API)
                self.assertEqual(create.call_count, 2)
                self.assertEqual(sum(call.kwargs['case_sum'] for call in create.call_args_list), expected)
                self.assertTrue(all(call.kwargs['summary_data']['meta']['api_count_by_scenario'] is mode
                                    for call in create.call_args_list))

    def test_ui_pytest_ignore_api_counting_flag(self):
        for kind in (TestCaseTypeEnum.UI, TestCaseTypeEnum.PYTEST):
            with self.subTest(kind=kind), patch(
                    'src.apps.test_center.services.reporting.test_suite.create.TestSuiteDetails.objects.create') as create:
                TestSuiteCreateService.create_detail(
                    suite_id=1, case_type=kind.value, project_product_id=1, test_env=0, case_id=1,
                    case_name='example', parametrize=[], status=TaskEnum.STAY_BEGIN.value, retry=0,
                    case_sum=7, api_case_revision_id=None, api_case_release_id=None,
                    config_checksum=None, api_count_by_scenario=False,
                )
                self.assertEqual(create.call_args.kwargs['case_sum'], 7)
                self.assertIsNone(create.call_args.kwargs['summary_data'])

    def test_closed_mode_failure_priority_and_warning_priority_are_consistent(self):
        for statuses, outcome in (
            ([TaskEnum.SUCCESS.value] * 4, 'success'),
            ([TaskEnum.SUCCESS.value, TaskEnum.FAIL.value, TaskEnum.SUCCESS.value, TaskEnum.WARNING.value], 'fail'),
            ([TaskEnum.SUCCESS.value] * 3 + [TaskEnum.WARNING.value], 'warning'),
        ):
            for mode in (True, False):
                detail = self.detail(mode)
                items = [{'status': status} for status in statuses]
                with self.subTest(statuses=statuses, mode=mode), \
                        patch.object(Results, 'get_result_data', return_value=items):
                    written = TestCounter.res_api(detail)
                    queried = Results.count_normalized_api_result(detail)
                self.assertEqual(written, queried)
                if mode:
                    self.assertEqual(sum(written.values()), 4)
                else:
                    self.assertEqual(written, {key: int(key == outcome) for key in ('success', 'fail', 'warning')})

    def test_unfinished_and_stopped_case_is_not_prematurely_counted_as_passed(self):
        for status, key in ((TaskEnum.STAY_BEGIN.value, 'stay_begin'), (TaskEnum.PROCEED.value, 'proceed'),
                            (TaskEnum.STOPPED.value, 'stopped')):
            detail = self.detail(False, status)
            counts = Counting.counter(detail, {'success': 3, 'fail': 0, 'warning': 1})
            summary = Summary.execution_status_counts_from_rows([{'case_sum': 1, 'status': status, **counts}])
            self.assertEqual(summary[key], 1)
            self.assertEqual(summary['success'] + summary['fail'] + summary['warning'], 0)

    def test_no_result_case_failure_and_summary_only_retention_use_single_case(self):
        detail = self.detail(False, TaskEnum.FAIL.value)
        for result in (None, {'__summary_skipped__': True}):
            with patch.object(Results, 'get_result_data', return_value=result):
                self.assertEqual(Results.count_normalized_api_result(detail), {'success': 0, 'fail': 1, 'warning': 0})

    def test_historical_records_without_snapshot_keep_scene_counting(self):
        detail = SimpleNamespace(summary_data=None)
        raw = {'success': 3, 'fail': 1, 'warning': 0}
        self.assertIs(Counting.counter(detail, raw), raw)

    def test_progress_rewrite_and_retry_reset_keep_counting_snapshot(self):
        detail = self.detail(False)
        detail.save = Mock()
        Results._save_locked_summary(detail, [{'status': 1}], {'snapshot_status': 'running'})
        self.assertIs(detail.summary_data['meta']['api_count_by_scenario'], False)
        reset = Counting.empty_summary(detail)
        self.assertEqual(reset, {'children': None, 'meta': {
            'api_count_by_scenario': False, 'api_scene_count': 1}})

    def test_scene_outcomes_remain_available_without_expanding_report_counters(self):
        detail = self.detail(False, TaskEnum.FAIL.value)
        detail.summary_data['meta']['api_scene_count'] = 4
        detail.save = Mock()
        Results._save_locked_summary(detail, [{'status': 1}] * 3 + [{'status': 0}], None)
        self.assertEqual(detail.case_sum, 1)
        self.assertEqual(detail.summary_data['meta']['api_scene_counter'],
                         {'success': 3, 'fail': 1, 'warning': 0})
        self.assertEqual(Counting.empty_summary(detail), {'children': None, 'meta': {
            'api_count_by_scenario': False, 'api_scene_count': 4}})

    def test_legacy_case_report_progress_does_not_cap_final_scene_snapshot(self):
        detail = self.detail(False, TaskEnum.PROCEED.value)
        detail.save = Mock()
        Results._save_locked_summary(detail, [{'status': 1}], None)
        detail.status = TaskEnum.FAIL.value
        Results._save_locked_summary(detail, [{'status': 1}] * 3 + [{'status': 0}], None)
        self.assertEqual(detail.summary_data['meta']['api_scene_count'], 4)
        self.assertEqual(detail.summary_data['meta']['api_scene_counter'],
                         {'success': 3, 'fail': 1, 'warning': 0})

    def test_actual_retry_operation_preserves_original_snapshot_without_reading_global_config(self):
        detail = self.detail(False, TaskEnum.FAIL.value)
        detail.save = Mock()
        with patch('src.apps.test_center.services.reporting.test_suite.retry.TestSuiteDetails.objects') as details, \
                patch.object(TestSuiteRetryService, 'ensure_infrastructure_reviewed'), \
                patch.object(TestSuiteRetryService, 'ensure_retry_supported'), \
                patch.object(TestSuiteRetryService, 'refresh_current_api_release'), \
                patch.object(Results, 'clear_result'), \
                patch('src.apps.system.services.configuration.system_config.SystemConfigService.get',
                      side_effect=AssertionError('重试不能重新读取全局统计配置')):
            details.select_for_update.return_value.get.return_value = detail
            TestSuiteRetryService.retry_detail.__wrapped__(TestSuiteRetryService, detail.id)
        self.assertEqual(detail.case_sum, 1)
        self.assertIs(detail.summary_data['meta']['api_count_by_scenario'], False)
        self.assertEqual(detail.status, TaskEnum.STAY_BEGIN.value)

    def test_interrupted_cleanup_preserves_snapshot_for_later_report_summary(self):
        detail = self.detail(False, TaskEnum.PROCEED.value)
        detail.retry = 1
        detail.save = Mock()
        with patch('src.apps.test_center.services.reporting.test_suite.timeout_recovery.TestSuiteDetails.objects') as details, \
                patch.object(TestSuiteTimeoutRecoveryService, 'close_api_traces'), \
                patch.object(TestSuiteTimeoutRecoveryService, 'save_empty_execution_record'), \
                patch.object(TestSuiteTimeoutRecoveryService, 'project_business_status'):
            details.select_for_update.return_value.get.return_value = detail
            self.assertTrue(TestSuiteTimeoutRecoveryService.fail_cleanup_interrupted.__wrapped__(
                TestSuiteTimeoutRecoveryService, detail))
        self.assertIs(detail.summary_data['meta']['api_count_by_scenario'], False)
        self.assertEqual(detail.case_sum, 1)

    def test_aggregate_exclusion_and_raw_totals_share_same_case_unit(self):
        rows = [{'type': TestCaseTypeEnum.API.value, 'case_sum': 1, 'status': 1,
                 'success': 1, 'fail': 0, 'warning': 0},
                {'type': TestCaseTypeEnum.API.value, 'case_sum': 1, 'status': 0,
                 'success': 0, 'fail': 1, 'warning': 0}]
        summary = Summary.counter_data_from_rows(rows)
        self.assertEqual((summary['case_sum'], summary['success'], summary['fail']), (2, 1, 1))
        rows[1]['is_excluded'] = True
        summary = Summary.counter_data_from_rows(rows)
        self.assertEqual((summary['case_sum'], summary['excluded_count'], summary['raw_case_sum']), (1, 1, 2))
