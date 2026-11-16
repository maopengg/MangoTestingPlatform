from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.conf import settings
from django.test import SimpleTestCase, override_settings
from pydantic import ValidationError

from src.apps.test_center.schemas.report_delivery import ReportDeliveryConfig
from src.apps.test_center.services.reporting.offline_report.service import OfflineReportService
from src.apps.test_center.services.reporting.offline_report.storage import ReportStorageService


class ReportHtmlDomainTests(SimpleTestCase):
    def test_old_config_defaults_to_platform_domain_and_normalizes_new_origin(self):
        self.assertEqual(ReportDeliveryConfig().html_public_base_url, '')
        config = ReportDeliveryConfig(html_public_base_url=' https://reports.example.com/ ')
        self.assertEqual(config.html_public_base_url, 'https://reports.example.com')
        for value in ('javascript:alert(1)', 'https://user:secret@reports.example.com',
                      'https://reports.example.com/path', 'https://reports.example.com?token=example',
                      'https://reports.example.com#test', 'https://reports.example.com:99999', None):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                ReportDeliveryConfig(html_public_base_url=value)

    def test_upload_pipeline_uses_scoped_domain_for_preview_and_download(self):
        for domain in ('', 'https://reports.example.com'):
            with self.subTest(domain=domain), patch(
                    'src.apps.test_center.services.reporting.offline_report.service.ReportStorageService') as storage:
                storage.return_value.local = None
                storage.return_value.key.return_value = 'example.html'
                OfflineReportService.upload_links(ReportDeliveryConfig(html_public_base_url=domain),
                                                  'example.html', b'example')
                storage.assert_called_once_with(public_base=domain or None)
                storage.return_value.save.assert_called_once_with('example.html', b'example')
                calls = storage.return_value.url.call_args_list
                self.assertEqual(calls[0].args, ('example.html', 'example.html', 604800))
                self.assertEqual(calls[1].args, ('example.html', 'example.html', 604800, True))

    @override_settings(FILE_STORAGE_BACKEND='tos', MINIO_STORAGE_ENDPOINT='tos-s3-cn-beijing.example.com',
                       MINIO_STORAGE_MEDIA_BUCKET_NAME='reports', MINIO_STORAGE_ACCESS_KEY='example-access',
                       MINIO_STORAGE_SECRET_KEY='example-secret', MINIO_STORAGE_REGION='cn-beijing',
                       MINIO_PUBLIC_BASE_URL='https://reports.tos-s3-cn-beijing.example.com')
    def test_only_report_public_links_change_upload_target_and_platform_setting_do_not(self):
        storage = ReportStorageService(public_base='https://html.example.com')
        self.assertEqual(storage.identity['endpoint'], 'tos-s3-cn-beijing.example.com')
        self.assertEqual(storage.identity['bucket'], 'reports')
        for download, disposition in ((False, 'inline'), (True, 'attachment')):
            url = urlsplit(storage.url('example.html', 'example.html', 300, download))
            self.assertEqual(url.hostname, 'html.example.com')
            self.assertEqual(url.path, '/example.html')
            query = parse_qs(url.query)
            self.assertIn('X-Tos-Signature', query)
            self.assertTrue(query['response-content-disposition'][0].startswith(disposition))
        self.assertEqual(settings.MINIO_PUBLIC_BASE_URL, 'https://reports.tos-s3-cn-beijing.example.com')
        self.assertEqual(ReportStorageService().public_base, settings.MINIO_PUBLIC_BASE_URL)
        with patch('src.apps.test_center.services.reporting.offline_report.storage.Minio') as client:
            storage.save('example.html', b'example')
            self.assertEqual(client.call_args.args[0], 'tos-s3-cn-beijing.example.com')

    @override_settings(FILE_STORAGE_BACKEND='minio', MINIO_STORAGE_ENDPOINT='minio.internal.example.com',
                       MINIO_STORAGE_MEDIA_BUCKET_NAME='reports', MINIO_STORAGE_ACCESS_KEY='example-access',
                       MINIO_STORAGE_SECRET_KEY='example-secret', MINIO_STORAGE_REGION='us-east-1',
                       MINIO_STORAGE_USE_VIRTUAL_HOST_STYLE=False,
                       MINIO_PUBLIC_BASE_URL='https://files.example.com')
    def test_minio_remains_supported_with_separate_html_origin(self):
        storage = ReportStorageService(public_base='https://html.example.com')
        preview = urlsplit(storage.url('example.html', 'example.html', 300))
        download = urlsplit(storage.url('example.html', 'example.html', 300, True))
        self.assertEqual(preview.hostname, 'html.example.com')
        self.assertEqual(download.hostname, 'html.example.com')
        self.assertTrue(parse_qs(preview.query)['response-content-disposition'][0].startswith('inline'))
        self.assertTrue(parse_qs(download.query)['response-content-disposition'][0].startswith('attachment'))
        self.assertEqual(settings.MINIO_PUBLIC_BASE_URL, 'https://files.example.com')
