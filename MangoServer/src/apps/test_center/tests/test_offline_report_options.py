from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from django.urls import resolve

from src.apps.test_center.api.serializers.test_suite import TestSuiteOfflineOptionsSerializer
from src.apps.test_center.api.views.test_suite import TestSuiteViews
from src.apps.test_center.enums.report_delivery import ReportSourceEnum
from src.apps.test_center.exceptions import TestCenterError
from src.apps.test_center.schemas.report_delivery import ReportDeliveryConfig
from src.apps.test_center.selectors.offline_report import OfflineReportSelector
from src.apps.test_center.services.offline_report import OfflineReportService
from src.apps.user.services.permission import PermissionMenuService, ProjectProductScopeService
from src.apps.user.tests.test_permissions import RolePermissionTests


class OfflineReportOptionsPermissionTests(RolePermissionTests):
    def test_options_and_download_require_report_export_permission(self):
        for action, method, path in (
            ('offline_options', 'get', '/api/system/test/suite/offline/options'),
            ('offline_export', 'post', '/api/system/test/suite/offline'),
            ('offline_publish', 'post', '/api/system/test/suite/offline/links'),
        ):
            self.assertEqual(resolve(path).func.actions[method], action)
            self.assert_grants(TestSuiteViews(), action, method, path, 'report:read')


class OfflineReportOptionsTests(SimpleTestCase):
    def test_validation_bounds_and_source_kind(self):
        for value in ({'source_kind': 'other', 'source_id': 1},
                      {'source_kind': 'suite', 'source_id': 0},
                      {'source_kind': 'group', 'source_id': 1, 'page_size': 101},
                      {'source_kind': 'suite', 'source_id': 1, 'page': 0}):
            self.assertFalse(TestSuiteOfflineOptionsSerializer(data=value).is_valid())

    def test_no_permission_does_not_query_reports(self):
        with patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=False), \
                patch.object(PermissionMenuService, 'permission_keys_for_user', return_value={'timing.tasks'}), \
                patch('src.apps.test_center.selectors.offline_report.TestSuite.objects') as manager:
            with self.assertRaises(TestCenterError):
                OfflineReportSelector.options(SimpleNamespace(id=1), ReportSourceEnum.SUITE, 2)
            manager.filter.assert_not_called()

    def test_options_are_scoped_paginated_and_use_lightweight_fields(self):
        for kind in ReportSourceEnum:
            with self.subTest(kind=kind), \
                    patch.object(OfflineReportSelector, 'require_permission'), \
                    patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=False), \
                    patch.object(ProjectProductScopeService, 'can_view_all_project_data', return_value=False), \
                    patch.object(ProjectProductScopeService, 'project_product_ids_for_user', return_value={7}), \
                    patch('src.apps.test_center.selectors.offline_report.TestSuite.objects') as suites, \
                    patch('src.apps.test_center.selectors.offline_report.ScheduleFireQuerySelector.scheduled_task_group_execution') as groups:
                query = MagicMock()
                suites.filter.return_value = query
                groups.return_value.filter.return_value = query
                query.filter.return_value = query
                query.exclude.return_value = query
                query.count.return_value = 23
                values = query.order_by.return_value.values.return_value
                values.__getitem__.return_value = [dict(id=3, test_env=5, status=0,
                                                       create_time=datetime(2026, 10, 28, 10, 0, 39))]
                result = OfflineReportSelector.options(SimpleNamespace(id=1), kind, 2, page=2, page_size=20)
                self.assertEqual(result['count'], 23)
                self.assertEqual(result['items'][0]['id'], 3)
                query.filter.assert_called_once_with(project_product_id__in={7})
                values.__getitem__.assert_called_once_with(slice(20, 40))
                query.exclude.assert_called_once_with(status__in=(2, 3))
                self.assertLessEqual(len(query.order_by.return_value.values.call_args.args), 5)
                if kind == ReportSourceEnum.SUITE:
                    suites.filter.assert_called_once_with(tasks_id=2, report_retained=True)
                    query.order_by.assert_called_once_with('-create_time', '-id')
                else:
                    groups.return_value.filter.assert_called_once_with(task_group_id=2, finished_at__isnull=False)
                    query.order_by.assert_called_once_with('-planned_at', '-id')

    def test_each_export_rebuilds_snapshot_for_both_sources(self):
        for kind in ReportSourceEnum:
            with self.subTest(kind=kind), \
                    patch('src.apps.test_center.services.offline_report.service.TestSuite.objects'), \
                    patch('src.apps.test_center.services.offline_report.service.ReportSnapshotService') as snapshots, \
                    patch('src.apps.test_center.services.offline_report.service.ReportHtmlService') as html, \
                    patch('src.apps.test_center.services.offline_report.service.SystemConfigService.get_platform_name', return_value='示例平台'):
                snapshots.suppresses_success_report.return_value = False
                snapshots.build.side_effect = [{'version': 1}, {'version': 2}]
                html.render.side_effect = [b'first', b'latest']
                first = OfflineReportService.render(kind, 3, ReportDeliveryConfig())
                latest = OfflineReportService.render(kind, 3, ReportDeliveryConfig())
                self.assertEqual((first[1], latest[1]), (b'first', b'latest'))
                self.assertEqual(snapshots.build.call_count, 2)
