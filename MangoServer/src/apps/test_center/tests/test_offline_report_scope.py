from types import SimpleNamespace
from datetime import datetime, timezone as datetime_timezone
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from django.utils import timezone
from mangotools.enums import TaskEnum

from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.enums.report_delivery import ReportSourceEnum
from src.apps.test_center.schemas.report_delivery import ReportDeliveryConfig
from src.apps.test_center.services.reporting.offline_report import OfflineReportService
from src.apps.test_center.services.reporting.offline_report.renderer import ReportHtmlService
from src.apps.test_center.services.reporting.offline_report.snapshot import ReportSnapshotService
from src.apps.test_center.tests.test_report_delivery import sample_snapshot


class OfflineReportScopeTests(SimpleTestCase):
    def test_display_time_uses_local_readable_seconds_without_iso_separator(self):
        with timezone.override('Asia/Shanghai'):
            self.assertEqual(ReportSnapshotService.display_time(datetime(2026, 10, 28, 10, 0, 39, 123456)),
                             '2026-10-28 10:00:39')
            self.assertEqual(ReportSnapshotService.display_time(datetime(2026, 10, 28, 2, 0, 39, tzinfo=datetime_timezone.utc)),
                             '2026-10-28 10:00:39')

    def test_old_config_defaults_to_failure_only_and_can_be_disabled(self):
        self.assertTrue(ReportDeliveryConfig.model_validate({'enabled': True}).failed_cases_only)
        self.assertFalse(ReportDeliveryConfig(failed_cases_only=False).failed_cases_only)

    def test_single_suite_filters_details_without_changing_full_statistics(self):
        now = timezone.now()
        rows = [SimpleNamespace(id=index, case_id=index, case_name=f'用例{index}', type=TestCaseTypeEnum.API.value,
                                status=status, fail=fail, is_excluded=index == 3, error_message='',
                                failure_reason='', failure_description='', update_time=now)
                for index, status, fail in [(1, TaskEnum.SUCCESS.value, 0), (2, TaskEnum.FAIL.value, 1),
                                           (3, TaskEnum.FAIL.value, 1), (4, TaskEnum.WARNING.value, 0),
                                           (5, TaskEnum.WARNING.value, 1)]]
        suite = SimpleNamespace(id=1, status=TaskEnum.FAIL.value, update_time=now, tasks=None,
                                execution_name='示例报告', create_time=now, test_env=0,
                                project_product=SimpleNamespace(name='产品', project=SimpleNamespace(name='项目')))
        counter = {'case_sum': 4, 'success': 1, 'fail': 2, 'warning': 1, 'excluded_count': 1}
        queryset = MagicMock()
        queryset.__getitem__.return_value = rows
        queryset.values_list.return_value = [(row.id, now) for row in rows]
        with patch('src.apps.test_center.services.reporting.offline_report.snapshot.TestSuite.objects') as suites, \
                patch('src.apps.test_center.services.reporting.offline_report.snapshot.TestSuiteDetails.objects') as details, \
                patch('src.apps.test_center.services.reporting.offline_report.snapshot.ExecutionResult.objects') as results, \
                patch('src.apps.test_center.services.reporting.offline_report.snapshot.EnvironmentEnum.get_value', return_value='示例环境'), \
                patch.object(ReportSnapshotService, 'suppresses_success_report', return_value=False), \
                patch('src.apps.test_center.services.reporting.offline_report.snapshot.TestSuiteSummaryService.counter_data', return_value=counter), \
                patch('src.apps.test_center.services.reporting.offline_report.snapshot.TestSuiteExecutionResultService.get_result_data', return_value={}):
            suites.select_related.return_value.filter.return_value.first.return_value = suite
            suites.filter.return_value.exists.return_value = True
            details.filter.return_value.order_by.return_value = queryset
            results.filter.return_value.values_list.return_value = []
            for only_failed, expected in [(True, [2, 3, 5]), (False, [1, 2, 3, 4, 5])]:
                snapshot = ReportSnapshotService.suite(1, ReportDeliveryConfig(failed_cases_only=only_failed))
                self.assertEqual([case['id'] for case in snapshot['cases']], expected)
                self.assertEqual(snapshot['summary'], counter)
            snapshot = ReportSnapshotService.suite(1, ReportDeliveryConfig(include_details=False))
            self.assertEqual(snapshot['cases'], [])

    def test_group_passes_same_scope_to_each_child_and_uses_group_link(self):
        child = {'name': '子任务', 'cases': [], 'summary': {}}
        report = SimpleNamespace(children=[SimpleNamespace(test_suite_id=1), SimpleNamespace(test_suite_id=2)],
                                 case_sum=10, success=9, fail=1, warning=0, excluded_count=0,
                                 task_group_name='示例任务组', failed_task_count=1, warning_task_count=0,
                                 project_name='项目', product_name='产品', test_environment='示例环境', planned_at='-')
        config = ReportDeliveryConfig()
        with patch('src.apps.task_center.services.scheduling.task_group_execution.ScheduledTaskGroupExecutionService.offline_report_source', return_value=(1, report)), \
                patch.object(ReportSnapshotService, 'suite', return_value=child) as build, \
                patch('src.apps.test_center.services.reporting.offline_report.snapshot.SystemConfigService.get', return_value='https://example.com'):
            snapshot = ReportSnapshotService.build(ReportSourceEnum.GROUP, 9, config)
        self.assertTrue(snapshot['failed_cases_only'])
        self.assertEqual(snapshot['online_url'], 'https://example.com/#/report/index?group_execution_id=9')
        self.assertEqual(snapshot['summary']['case_sum'], 10)
        self.assertEqual([call.args for call in build.call_args_list], [(1, config), (2, config)])

    def test_notice_and_link_are_only_shown_when_enabled_and_are_escaped(self):
        snapshot = sample_snapshot()
        snapshot.update(failed_cases_only=True, online_url='https://example.com/#/report/system/details?id=1&name="quoted"')
        content = ReportHtmlService.render(snapshot, '示例平台').decode()
        self.assertIn('为避免 HTML 数据过大', content)
        self.assertIn('完整数据请前往', content)
        self.assertIn('需要内网访问', content)
        self.assertIn('&amp;name=&quot;quoted&quot;', content)
        snapshot['failed_cases_only'] = False
        self.assertNotIn('为避免 HTML 数据过大', ReportHtmlService.render(snapshot, '示例平台').decode())

    def test_online_link_uses_existing_domain_and_rejects_unsafe_config(self):
        for domain, expected in [('https://example.com/', 'https://example.com/#/report/system/details?id=1'),
                                 ('', ''), ('javascript:alert(1)', ''), ('https://user:password@example.com', '')]:
            with self.subTest(domain=domain), patch('src.apps.test_center.services.reporting.offline_report.snapshot.SystemConfigService.get', return_value=domain):
                self.assertEqual(ReportSnapshotService.online_url(ReportSourceEnum.SUITE, 1), expected)

    def test_sample_honors_saved_scope(self):
        for flag in (True, False):
            with patch.object(OfflineReportService, 'config', return_value=ReportDeliveryConfig(failed_cases_only=flag)), \
                    patch('src.apps.test_center.services.reporting.offline_report.service.SystemConfigService.get_platform_name', return_value='示例平台'), \
                    patch.object(ReportSnapshotService, 'online_url', return_value='https://example.com/#/report/index'):
                content = OfflineReportService.sample().decode()
            self.assertEqual('示例查询用例' in content, not flag)
            self.assertIn('示例数据校验用例', content)
            self.assertEqual('为避免 HTML 数据过大' in content, flag)

    def test_standalone_template_embeds_styles_and_does_not_expand_report_values(self):
        snapshot = sample_snapshot()
        snapshot['name'] = '${platform_name} <script>示例</script>'
        content = ReportHtmlService.render(snapshot, '示例平台').decode()
        self.assertIn('${platform_name} &lt;script&gt;示例&lt;/script&gt;', content)
        self.assertRegex(content, r'<style>\s*:root\{')
        self.assertIn('mango-report-head', content)
        self.assertNotIn('href="report.css"', content)
        self.assertNotIn('$scope_notice', content)
