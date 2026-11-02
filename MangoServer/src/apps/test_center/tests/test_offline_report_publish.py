from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from src.apps.test_center.api.views.test_suite import TestSuiteViews
from src.apps.test_center.enums.report_delivery import ReportSourceEnum
from src.apps.test_center.exceptions import REPORT_ARTIFACT_INVALID, REPORT_LOCAL_LINK_UNAVAILABLE, TestCenterError
from src.apps.test_center.schemas.report_delivery import ReportDeliveryConfig
from src.apps.test_center.selectors.offline_report import OfflineReportSelector
from src.apps.test_center.services.offline_report import OfflineReportService


class OfflineReportPublishTests(SimpleTestCase):
    def test_each_publish_renders_latest_content_and_uploads_a_new_object(self):
        config = ReportDeliveryConfig(enabled=False, link_ttl_seconds=300)
        for kind in ReportSourceEnum:
            with self.subTest(kind=kind), \
                    patch('src.apps.test_center.services.offline_report.service.ReportStorageService') as storage_class, \
                    patch.object(OfflineReportService, 'config', return_value=config), \
                    patch.object(OfflineReportService, 'render', side_effect=[('report.html', b'first'), ('report.html', b'latest')]) as render:
                storage = storage_class.return_value
                storage.local = None
                storage.key.side_effect = lambda key: f'offline_reports/{key}.html'
                storage.url.side_effect = lambda key, filename, seconds, download=False: f'https://reports.example.com/{key}?download={download}'
                first = OfflineReportService.publish(kind, 3)
                latest = OfflineReportService.publish(kind, 3)
                self.assertEqual(render.call_count, 2)
                render.assert_called_with(kind, 3, config)
                keys = [call.args[0] for call in storage.save.call_args_list]
                self.assertEqual(len(set(keys)), 2)
                self.assertEqual([call.args[1] for call in storage.save.call_args_list], [b'first', b'latest'])
                self.assertNotEqual(first['preview_url'], latest['preview_url'])
                self.assertNotEqual(latest['preview_url'], latest['download_url'])
                self.assertEqual(latest['filename'], 'report.html')
                self.assertTrue(latest['expires_at'])
                self.assertEqual([call.args[-1] for call in storage.url.call_args_list if len(call.args) == 4], [True, True])

    def test_local_storage_does_not_upload_or_render_twice_before_download_fallback(self):
        with patch('src.apps.test_center.services.offline_report.service.ReportStorageService') as storage, \
                patch.object(OfflineReportService, 'render') as render:
            storage.return_value.local = object()
            with self.assertRaises(TestCenterError) as caught:
                OfflineReportService.publish(ReportSourceEnum.SUITE, 3)
            self.assertEqual(caught.exception.code, REPORT_LOCAL_LINK_UNAVAILABLE.code)
            render.assert_not_called()
            storage.return_value.save.assert_not_called()

    def test_http_publish_checks_scope_before_upload_and_does_not_cache_signed_urls(self):
        user = SimpleNamespace(id=1)
        request = SimpleNamespace(user=SimpleNamespace(user_obj=user), data={'source_kind': 'group', 'source_id': 3})
        with patch.object(OfflineReportSelector, 'require_permission') as permission, \
                patch.object(OfflineReportSelector, 'require_product') as scope, \
                patch('src.apps.test_center.api.views.test_suite.ReportSnapshotService.source_product_id', return_value=7), \
                patch.object(OfflineReportService, 'publish', return_value={'preview_url': 'https://reports.example.com/report.html'}) as publish:
            response = TestSuiteViews().offline_publish(request)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['Cache-Control'], 'no-store')
            permission.assert_called_once_with(user)
            scope.assert_called_once_with(user, 7)
            publish.assert_called_once_with(ReportSourceEnum.GROUP, 3)
            publish.reset_mock()
            scope.side_effect = TestCenterError(REPORT_ARTIFACT_INVALID)
            response = TestSuiteViews().offline_publish(request)
            self.assertEqual(response.data['code'], REPORT_ARTIFACT_INVALID.code)
            publish.assert_not_called()
