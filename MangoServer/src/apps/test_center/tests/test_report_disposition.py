from src.apps.user.services.http_permission_registry import permission_for_view
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory
from mangotools.enums import TaskEnum

from src.apps.test_center.enums import ReportFailureReasonEnum, TestCaseTypeEnum
from src.apps.test_center.exceptions import TestCenterError
from src.apps.test_center.services.test_suite.disposition import TestSuiteDispositionService
from src.apps.test_center.services.test_suite.summary import TestSuiteSummaryService
from src.apps.test_center.api.views.test_suite_details import TestSuiteDetailsViews
from src.apps.system.services.enum_catalog import EnumCatalogService


class ReportDispositionTests(SimpleTestCase):
    def setUp(self):
        self.detail = SimpleNamespace(id=2, test_suite_id=1, status=0, fail=2, is_excluded=False,
                                      summary_data=None,
                                      project_product_id=3,
                                      failure_reason='', failure_description='')
        self.saved = []
        self.detail.save = lambda **kwargs: self.saved.append(kwargs)
        self.suite = SimpleNamespace(id=1, status=0)
        for name, target in [('details', 'TestSuiteDetails.objects'), ('suites', 'TestSuite.objects')]:
            mocked = patch(f'src.apps.test_center.services.test_suite.disposition.{target}')
            setattr(self, name, mocked.start())
            self.addCleanup(mocked.stop)
        atomic = patch('src.apps.test_center.services.test_suite.disposition.transaction.atomic', side_effect=nullcontext)
        atomic.start()
        self.addCleanup(atomic.stop)
        # ORM 已由内存替身隔离；跳过导入时绑定的事务装饰器，避免连接真实数据库。
        unwrapped_update = TestSuiteDispositionService.update.__wrapped__
        update = patch.object(TestSuiteDispositionService, 'update', side_effect=lambda *args, **kwargs: unwrapped_update(TestSuiteDispositionService, *args, **kwargs))
        update.start()
        self.addCleanup(update.stop)
        environments = patch('src.apps.system.services.system_config.SystemConfigService.get_environment_display_names', return_value={})
        environments.start()
        self.addCleanup(environments.stop)
        self.details.filter.return_value.values_list.return_value.first.return_value = 1
        self.details.filter.return_value.exists.return_value = False
        self.details.select_for_update.return_value.get.return_value = self.detail
        self.suites.select_for_update.return_value.filter.return_value.first.side_effect = lambda: self.suite

    def test_fields_are_independent_and_original_result_is_unchanged(self):
        TestSuiteDispositionService.update(2, {'failure_reason': ReportFailureReasonEnum.PRODUCT_PENDING.value,
                                              'failure_description': '等待开发修复'})
        self.assertFalse(self.detail.is_excluded)
        TestSuiteDispositionService.update(2, {'is_excluded': True})
        self.assertEqual(self.detail.status, 0)
        self.assertEqual(self.detail.fail, 2)
        self.assertEqual(self.detail.failure_description, '等待开发修复')
        self.assertNotIn('update_time', self.saved[-1]['update_fields'])
        TestSuiteDispositionService.update(2, {'is_excluded': False})
        self.assertEqual(self.detail.failure_reason, 'product_pending')

    def test_mcp_diagnosis_enforces_scope_and_preserves_exclusion(self):
        from src.common.exceptions import MangoServerError
        self.detail.is_excluded = True
        user = SimpleNamespace(id=7)
        with patch('src.apps.test_center.services.test_suite.disposition.PermissionMenuService.is_effective_super_admin', return_value=False), \
                patch('src.apps.test_center.services.test_suite.disposition.ProjectProductScopeService.has_project_product', return_value=False):
            with self.assertRaises(MangoServerError):
                TestSuiteDispositionService.update_diagnosis(2, 'product_pending', '等待修复', user=user)
        self.assertEqual(self.saved, [])
        with patch('src.apps.test_center.services.test_suite.disposition.PermissionMenuService.is_effective_super_admin', return_value=False), \
                patch('src.apps.test_center.services.test_suite.disposition.ProjectProductScopeService.has_project_product', return_value=True):
            result = TestSuiteDispositionService.update_diagnosis(2, 'product_pending', '等待修复', user=user)
        self.assertTrue(result['is_excluded'])
        self.assertEqual(self.saved[-1]['update_fields'], ['failure_reason', 'failure_description'])
        self.assertEqual(self.detail.status, 0)

    def test_backend_allows_exclusion_without_reason_but_rejects_invalid_fields(self):
        self.assertTrue(TestSuiteDispositionService.update(2, {'is_excluded': True})['is_excluded'])
        for values in [{'status': 1}, {'is_excluded': 'true'}, {'failure_reason': 'invalid'},
                       {'failure_description': 'x' * 1001}, {}]:
            with self.subTest(values=values), self.assertRaises(TestCenterError):
                TestSuiteDispositionService.update(2, values)

    def test_mcp_explicit_exclude_and_restore_preserve_original_failure(self):
        user = SimpleNamespace(id=7)
        with patch('src.apps.test_center.services.test_suite.disposition.PermissionMenuService.is_effective_super_admin', return_value=False), \
                patch('src.apps.test_center.services.test_suite.disposition.ProjectProductScopeService.has_project_product', return_value=True):
            for flag in (True, False):
                result = TestSuiteDispositionService.update_diagnosis(
                    2, 'test_case', '用例已取消发布，保留原始失败记录', user=user, is_excluded=flag,
                )
                self.assertIs(result['is_excluded'], flag)
                self.assertEqual((self.detail.status, self.detail.fail), (0, 2))
                self.assertEqual(set(self.saved[-1]['update_fields']), {'failure_reason', 'failure_description', 'is_excluded'})
                self.assertNotIn('update_time', self.saved[-1]['update_fields'])

    def test_mcp_exclusion_cannot_bypass_product_scope(self):
        user = SimpleNamespace(id=7)
        from src.common.exceptions import MangoServerError
        with patch('src.apps.test_center.services.test_suite.disposition.PermissionMenuService.is_effective_super_admin', return_value=False), \
                patch('src.apps.test_center.services.test_suite.disposition.ProjectProductScopeService.has_project_product', return_value=False):
            with self.assertRaises(MangoServerError):
                TestSuiteDispositionService.update_diagnosis(2, 'test_case', '说明', user=user, is_excluded=True)
        self.assertFalse(self.detail.is_excluded)
        self.assertEqual(self.saved, [])

    def test_running_or_successful_results_cannot_be_excluded(self):
        self.suite.status = TaskEnum.PROCEED.value
        with self.assertRaises(TestCenterError):
            TestSuiteDispositionService.update(2, {'is_excluded': True})
        self.suite.status = 1
        self.detail.status, self.detail.fail = 1, 0
        with self.assertRaises(TestCenterError):
            TestSuiteDispositionService.update(2, {'is_excluded': True})

    def test_retry_resets_only_target_disposition(self):
        from src.apps.test_center.services.test_suite.retry import TestSuiteRetryService
        self.detail.is_excluded = True
        self.detail.failure_reason = 'product_pending'
        self.detail.failure_description = '等待修复'
        with patch('src.apps.test_center.services.test_suite.retry.TestSuiteDetails.objects') as manager, \
                patch('src.apps.test_center.services.test_suite.retry.transaction.atomic', side_effect=nullcontext), \
                patch.object(TestSuiteRetryService, 'refresh_current_api_release'), \
                patch('src.apps.test_center.services.test_suite.retry.TestSuiteExecutionResultService.clear_result') as clear:
            manager.select_for_update.return_value.get.return_value = self.detail
            TestSuiteRetryService.retry_detail.__wrapped__(TestSuiteRetryService, 2)
        self.assertFalse(self.detail.is_excluded)
        self.assertEqual(self.detail.failure_reason, '')
        self.assertEqual(self.detail.failure_description, '')
        clear.assert_called_once_with([2])

    def test_whole_scenario_exclusion_and_restore_keep_raw_counts(self):
        rows = [dict(type=TestCaseTypeEnum.API.value, status=0, case_sum=10, success=8, fail=2, warning=0,
                     is_excluded=True), dict(type=TestCaseTypeEnum.UI.value, status=1, case_sum=3,
                                            success=3, fail=0, warning=0)]
        result = TestSuiteSummaryService.counter_data_from_rows(rows)
        self.assertEqual((result['case_sum'], result['success'], result['fail']), (3, 3, 0))
        self.assertEqual((result['excluded_count'], result['excluded_items'], result['raw_case_sum']), (10, 1, 13))
        self.assertEqual(TestSuiteSummaryService.execution_status_counts_from_rows(rows)['fail'], 2)
        rows[0]['is_excluded'] = False
        self.assertEqual(TestSuiteSummaryService.counter_data_from_rows(rows)['fail'], 2)

    def test_all_excluded_counts_as_passed_without_adding_success_cases(self):
        summary = TestSuiteSummaryService.effective_summary_from_rows([
            dict(status=0, case_sum=1, fail=1, success=0, warning=0, is_excluded=True),
        ])
        self.assertEqual((summary['total'], summary['success'], summary['excluded_count']), (0, 0, 1))
        self.assertEqual(TestSuiteSummaryService.conclusion_status(0, summary, 0), 1)

    def test_exclude_permission_is_registered_and_not_given_to_guests(self):
        from src.apps.user.services.permission import PermissionMenuService
        self.assertIn('change', PermissionMenuService.MENU_ACTIONS['report'])
        self.assertNotIn('change', __import__('src.apps.user.services.permission', fromlist=['GUEST_ALLOWED_ACTIONS']).GUEST_ALLOWED_ACTIONS)
        self.assertIn({'key': 'product_pending', 'title': '产品缺陷待修复'}, EnumCatalogService.catalog()['report_failure_reason'])

    def test_endpoint_rejects_product_scope_before_mutating(self):
        self.assertEqual(permission_for_view(TestSuiteDetailsViews, 'update_disposition'), 'report:change')
        request = APIRequestFactory().post('/api/test/suite/details/disposition',
                                          {'id': 2, 'is_excluded': True}, format='json')
        with patch.object(TestSuiteDetailsViews, '_has_detail_scope', return_value=False), \
                patch.object(TestSuiteDispositionService, 'update') as update:
            response = TestSuiteDetailsViews.as_view({'post': 'update_disposition'})(request)
        self.assertNotEqual(response.data['code'], 200)
        update.assert_not_called()
