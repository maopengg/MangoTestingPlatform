from src.apps.user.services.authorization.http_permission_registry import permission_for_view
from types import SimpleNamespace
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlsplit
from pathlib import Path
import re

from django.test import SimpleTestCase, override_settings
from pydantic import ValidationError

from src.apps.test_center.enums.report_delivery import ReportSourceEnum
from src.apps.test_center.exceptions import TestCenterError
from src.apps.test_center.schemas.report_delivery import ReportDeliveryConfig
from src.apps.test_center.selectors.offline_report import OfflineReportSelector
from src.apps.test_center.services.reporting.offline_report import OfflineReportService
from src.apps.test_center.services.reporting.report_delivery import ReportDeliveryService
from src.apps.test_center.services.reporting.offline_report.renderer import ReportHtmlService
from src.apps.test_center.services.reporting.offline_report.snapshot import ReportSnapshotService
from src.apps.test_center.services.reporting.offline_report.storage import ReportStorageService


def sample_snapshot():
    return {'name': '示例报告', 'product': '示例项目 / 产品', 'environment': '测试环境',
            'started_at': '-', 'generated_at': '-', 'result': '失败', 'rate': '50.00%',
            'summary': {'case_sum': 2, 'success': 1, 'fail': 1, 'warning': 0, 'excluded_count': 1},
            'suites': [{'name': '模块一', 'cases': [{'id': 1, 'name': '<script>alert(1)</script>',
                'type': 'API', 'status': '失败', 'excluded': True, 'reason': '测试平台问题',
                'description': '已定位', 'payload': {'headers': [{'key': 'Authorization', 'value': 'secret-value'}]}}]}]}


class ReportDeliveryTests(SimpleTestCase):
    def test_feishu_access_section_is_compact_and_groups_all_buttons(self):
        card = {'elements': [{'tag': 'action', 'actions': [
            {'tag': 'button', 'url': 'https://example.com/report'},
            {'tag': 'button', 'url': 'https://example.com/other'},
        ]}]}
        links = {'查看离线报告': 'https://example.com/preview', '下载 HTML': 'https://example.com/download'}
        ReportDeliveryService.add_feishu_access_section(card, 'https://example.com/report', links)
        self.assertFalse(any(item['tag'] == 'table' for item in card['elements']))
        self.assertFalse(any(item['tag'] == 'note' for item in card['elements']))
        buttons = [item for item in card['elements'] if item['tag'] == 'action'][-1]['actions']
        self.assertEqual([item for item in card['elements'] if item['tag'] == 'action'][-1]['layout'], 'trisection')
        self.assertEqual([button['text']['content'] for button in buttons], ['查看平台报告（需要内网访问）', '查看离线报告', '下载 HTML'])
        self.assertEqual(buttons[2]['url'], 'https://example.com/download')
        self.assertEqual(card['elements'][0]['actions'], [{'tag': 'button', 'url': 'https://example.com/other'}])

    def test_feishu_access_section_omits_unavailable_offline_links(self):
        card = {'elements': []}
        ReportDeliveryService.add_feishu_access_section(card, 'https://example.com/report', {})
        buttons = next(item for item in card['elements'] if item['tag'] == 'action')['actions']
        self.assertEqual(len(buttons), 1)
        self.assertEqual(buttons[0]['text']['content'], '查看平台报告（需要内网访问）')

    @override_settings(FILE_STORAGE_BACKEND='local')
    def test_local_storage_notification_explains_missing_links_without_claiming_render_failed(self):
        session = ReportDeliveryService(ReportDeliveryConfig(enabled=True))
        session.filename, session.content = 'report.html', b'html'
        notice = SimpleNamespace(mail=None, work_weixin=None, feishu='https://example.com/webhook', dingding=None)
        with patch('src.apps.test_center.services.reporting.report_delivery.FeiShuSend') as feishu:
            feishu.return_value.build_test_report_card.return_value = {'elements': []}
            session.send(notice, '示例平台', 'https://example.com/report', lambda: {})
        card = feishu.return_value.send_interactive_card.call_args.args[0]
        messages = [item.get('text', {}).get('content', '') for item in card['elements']]
        self.assertTrue(any('本地文件存储' in message and '手动下载 HTML' in message for message in messages))
        self.assertFalse(any('生成失败' in message for message in messages))

    def test_safe_defaults_and_validation(self):
        self.assertFalse(ReportDeliveryConfig().enabled)
        self.assertTrue(ReportDeliveryConfig().failed_cases_only)
        self.assertEqual(set(ReportDeliveryConfig().model_dump()), {
            'version', 'enabled', 'include_details', 'failed_cases_only', 'include_screenshots', 'link_ttl_seconds',
            'html_public_base_url',
        })
        for values in ({'feishu': 'attachment'}, {'storage': 'tos'}, {'retention_days': 1}, {'auto_generate': False},
                       {'failure_policy': 'strict'}, {'link_mode': 'download'}, {'max_size_mb': 25}, {'payload_scope': 'all'},
                       {'public_base_url': 'https://user:password@reports.example.com'},
                       {'endpoint': 'https://storage.example.com'}, {'public_base_url': 'https://reports.example.com/prefix'}):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                ReportDeliveryConfig(**values)

    def test_offline_html_is_escaped_and_secret_free(self):
        content = ReportHtmlService.render(sample_snapshot(), '示例平台').decode()
        self.assertEqual(content.count('<script>'), 1)
        self.assertNotIn('<script>alert(1)</script>', content)
        self.assertNotIn('secret-value', content)
        self.assertIn('&lt;script&gt;', content)
        self.assertIn('已排除', content)
        self.assertIn('已定位', content)
        self.assertIn("default-src 'none'", content)
        self.assertNotIn('src="http', content)

    def test_nested_and_text_credentials_are_redacted(self):
        for value in ({'token': 'private-value'}, '{"password":"private-value"}',
                      'token=private-value&user=sample', 'Authorization: Bearer private-value'):
            self.assertNotIn('private-value', str(ReportHtmlService.redact(value)))

    def test_only_link_delivery_uploads_and_failed_signing_deletes_object(self):
        storage = MagicMock(local=None)
        storage.key.return_value = 'offline_reports/example.html'
        storage.url.side_effect = RuntimeError('private')
        with patch('src.apps.test_center.services.reporting.offline_report.service.ReportStorageService', return_value=storage):
            with self.assertRaises(TestCenterError):
                OfflineReportService.upload_links(ReportDeliveryConfig(), 'example.html', b'example')
        storage.save.assert_called_once()
        storage.delete.assert_called_once_with('offline_reports/example.html')

    def test_email_uses_the_same_links_as_bots_without_attachments(self):
        notice = SimpleNamespace(mail=['reader@example.com'], work_weixin=None, feishu=None, dingding=None)
        with patch.object(OfflineReportService, 'config', return_value=ReportDeliveryConfig(enabled=True)), \
             patch.object(OfflineReportService, 'render', return_value=('report.html', b'example')), \
             patch.object(OfflineReportService, 'upload_links', return_value={'查看离线报告': 'https://example.com/preview', '下载 HTML': 'https://example.com/download'}) as upload, \
             patch('src.apps.test_center.services.reporting.report_delivery.EmailSend') as sender:
            sender.return_value.build_test_report_html.return_value = '<p>example</p>'
            sender.return_value.build_test_report_title.return_value = '❌示例平台自动化测试报告 - 失败'
            session = ReportDeliveryService.prepare(ReportSourceEnum.SUITE, 1, notice)
            session.send(notice, '示例平台', 'https://example.com', lambda: {
                'send_user': 'sender@example.com', 'email_host': 'smtp.example.com', 'stamp_key': 'example'})
        upload.assert_called_once()
        args = sender.return_value.send_mail.call_args
        self.assertEqual(args.args[0], '❌示例平台自动化测试报告 - 失败')
        self.assertNotIn('attachments', args.kwargs)
        self.assertIn('https://example.com/preview', args.args[1])
        self.assertIn('https://example.com/download', args.args[1])

    def test_each_resend_renders_latest_data_and_links_are_shared_across_channels(self):
        notice = SimpleNamespace(mail=None, work_weixin='https://example.com/wechat', feishu='https://example.com/feishu', dingding=None)
        with patch.object(OfflineReportService, 'config', return_value=ReportDeliveryConfig(enabled=True)), \
             patch.object(OfflineReportService, 'render', side_effect=[('a.html', b'first'), ('b.html', b'latest')]) as render, \
             patch.object(OfflineReportService, 'upload_links', return_value={'下载离线报告': 'https://example.com/report.html'}) as upload, \
             patch('src.apps.test_center.services.reporting.report_delivery.WeChatSend') as wechat, \
             patch('src.apps.test_center.services.reporting.report_delivery.FeiShuSend') as feishu:
            wechat.return_value.build_test_report_markdown.return_value = 'example'
            feishu.return_value.build_test_report_card.side_effect = lambda: {'elements': []}
            for _ in range(2):
                session = ReportDeliveryService.prepare(ReportSourceEnum.SUITE, 1, notice)
                session.send(notice, '示例平台', 'https://example.com', lambda: {})
        self.assertEqual(render.call_count, 2)
        self.assertEqual(upload.call_count, 2)
        self.assertEqual(upload.call_args.args[2], b'latest')

    def test_local_private_storage_round_trip(self):
        with TemporaryDirectory() as directory, override_settings(FILE_STORAGE_BACKEND='local', RUNTIME_DIR=directory):
            storage = ReportStorageService()
            key = storage.key('sample')
            storage.save(key, b'html')
            self.assertEqual(storage.read(key), b'html')
            with self.assertRaises(TestCenterError):
                storage.url(key, 'sample.html', 300)
            storage.delete(key)
            self.assertFalse(storage.local.exists(key))

    def test_minio_url_signs_final_host_and_download_headers(self):
        with override_settings(FILE_STORAGE_BACKEND='minio', RUNTIME_DIR='/tmp/example', MINIO_STORAGE_ENDPOINT='internal.example.com',
                               MINIO_STORAGE_MEDIA_BUCKET_NAME='reports', MINIO_STORAGE_ACCESS_KEY='example-access',
                               MINIO_STORAGE_SECRET_KEY='example-secret', MINIO_PUBLIC_BASE_URL='https://reports.example.com', FILE_STORAGE_ROOT=''):
            url = ReportStorageService().url('offline_reports/a.html', 'a.html', 300, True)
        self.assertEqual(urlsplit(url).hostname, 'reports.example.com')
        query = parse_qs(urlsplit(url).query)
        self.assertIn('attachment', query['response-content-disposition'][0])
        self.assertEqual(query['X-Amz-Expires'], ['300'])

    def test_tos_uses_native_custom_domain_signature(self):
        with override_settings(FILE_STORAGE_BACKEND='tos', RUNTIME_DIR='/tmp/example', MINIO_STORAGE_ENDPOINT='tos-cn-beijing.example.com',
                               MINIO_STORAGE_MEDIA_BUCKET_NAME='reports', MINIO_STORAGE_ACCESS_KEY='example-access',
                               MINIO_STORAGE_SECRET_KEY='example-secret', MINIO_PUBLIC_BASE_URL='https://reports.example.com', FILE_STORAGE_ROOT=''):
            url = ReportStorageService().url('offline_reports/a.html', 'a.html', 300, True)
        self.assertEqual(urlsplit(url).hostname, 'reports.example.com')
        self.assertNotIn('/reports/', urlsplit(url).path)
        self.assertIn('X-Tos-Signature', parse_qs(urlsplit(url).query))

    def test_tos_standard_bucket_domain_is_not_duplicated(self):
        with override_settings(FILE_STORAGE_BACKEND='tos', RUNTIME_DIR='/tmp/example', MINIO_STORAGE_ENDPOINT='tos-cn-beijing.example.com',
                               MINIO_STORAGE_MEDIA_BUCKET_NAME='reports', MINIO_STORAGE_ACCESS_KEY='example-access',
                               MINIO_STORAGE_SECRET_KEY='example-secret', MINIO_PUBLIC_BASE_URL='https://reports.tos-s3-cn-beijing.example.com', FILE_STORAGE_ROOT=''):
            url = ReportStorageService().url('offline_reports/a.html', 'a.html', 300)
        self.assertEqual(urlsplit(url).hostname, 'reports.tos-s3-cn-beijing.example.com')
        self.assertIn('X-Amz-Signature', parse_qs(urlsplit(url).query))
        self.assertNotIn('X-Tos-Signature', parse_qs(urlsplit(url).query))

    @override_settings(FILE_STORAGE_BACKEND='tos', MINIO_STORAGE_ENDPOINT='tos-s3-cn-beijing.example.com',
                       MINIO_STORAGE_MEDIA_BUCKET_NAME='reports', MINIO_STORAGE_ACCESS_KEY='example-access',
                       MINIO_STORAGE_SECRET_KEY='example-secret', MINIO_STORAGE_USE_VIRTUAL_HOST_STYLE=True,
                       MINIO_PUBLIC_BASE_URL='https://reports.example.com')
    def test_tos_s3_storage_uses_s3_for_upload_read_and_delete(self):
        with patch('src.apps.test_center.services.reporting.offline_report.storage.Minio') as s3, \
             patch('src.apps.test_center.services.reporting.offline_report.storage.TosClientV2') as native:
            storage = ReportStorageService()
            s3.return_value.get_object.return_value.read.return_value = b'html'
            storage.save('sample.html', b'html')
            self.assertEqual(storage.read('sample.html'), b'html')
            storage.delete('sample.html')
        native.assert_not_called()
        s3.return_value.put_object.assert_called_once()
        s3.return_value.remove_object.assert_called_once_with('reports', 'sample.html')
        s3.return_value.get_object.return_value.release_conn.assert_called_once()

    @override_settings(FILE_STORAGE_BACKEND='tos', MINIO_STORAGE_ENDPOINT='tos-s3-cn-beijing.example.com',
                       MINIO_STORAGE_MEDIA_BUCKET_NAME='reports', MINIO_STORAGE_ACCESS_KEY='example-access',
                       MINIO_STORAGE_SECRET_KEY='example-secret', MINIO_PUBLIC_BASE_URL='https://reports.example.com')
    def test_custom_domain_signing_converts_s3_endpoint_for_native_sdk(self):
        with patch('src.apps.test_center.services.reporting.offline_report.storage.TosClientV2') as native:
            ReportStorageService().url('sample.html', 'sample.html', 300)
        self.assertEqual(native.call_args.args[2], 'https://tos-cn-beijing.example.com')
        self.assertTrue(native.return_value.pre_signed_url.call_args.kwargs['is_custom_domain'])
        native.return_value.close.assert_called_once()

    @override_settings(FILE_STORAGE_BACKEND='tos', MINIO_STORAGE_ENDPOINT='tos-cn-beijing.internal.example.com',
                       MINIO_STORAGE_MEDIA_BUCKET_NAME='reports', MINIO_STORAGE_ACCESS_KEY='example-access',
                       MINIO_STORAGE_SECRET_KEY='example-secret', MINIO_PUBLIC_BASE_URL='https://reports.tos-cn-beijing.example.com')
    def test_native_tos_public_endpoint_can_differ_from_internal_endpoint(self):
        url = ReportStorageService().url('sample.html', 'sample.html', 300)
        self.assertEqual(urlsplit(url).hostname, 'reports.tos-cn-beijing.example.com')
        self.assertIn('X-Tos-Signature', parse_qs(urlsplit(url).query))

    def test_storage_failure_logs_only_safe_error_metadata(self):
        error = RuntimeError('Authorization: private-secret https://example.com?Signature=private')
        error.code = 'secret=private'
        error.status_code = 400
        with patch('src.apps.test_center.services.reporting.offline_report.service.log.system.warning') as warning:
            OfflineReportService.log_storage_failure('upload', error)
        message = warning.call_args.args[0]
        self.assertIn('stage=upload', message)
        self.assertIn('status=400', message)
        self.assertNotIn('private', message)
        self.assertNotIn('Authorization', message)

    def test_storage_always_inherits_platform_credentials_and_prefix(self):
        with override_settings(FILE_STORAGE_BACKEND='minio', MINIO_STORAGE_ENDPOINT='storage.example.com',
                               MINIO_STORAGE_MEDIA_BUCKET_NAME='reports', MINIO_STORAGE_ACCESS_KEY='example-access',
                               MINIO_STORAGE_SECRET_KEY='example-secret', FILE_STORAGE_ROOT='example/test'):
            storage = ReportStorageService()
            self.assertEqual(storage.identity['endpoint'], 'storage.example.com')
            self.assertEqual(storage.identity['bucket'], 'reports')
            self.assertEqual(storage._credentials(), ('example-access', 'example-secret'))
            self.assertTrue(storage.key('sample').startswith('example/test/offline_reports/'))

    def test_screenshot_reader_never_follows_http_or_parent_path(self):
        with patch('src.apps.test_center.services.reporting.offline_report.snapshot.default_storage.open') as opened:
            self.assertEqual(ReportSnapshotService.images({'screenshot': 'https://example.com/image.png',
                'child': {'screenshot_path': '../image.png'}}), [])
            opened.assert_not_called()

    def test_mobile_report_keeps_case_and_investigation_in_one_vertical_block(self):
        content = ReportHtmlService.render(sample_snapshot(), '示例平台').decode()
        self.assertIn('thead{display:none}', content)
        self.assertIn('td{display:block;', content)
        self.assertIn('data-label="结果："', content)
        self.assertIn('content:attr(data-label)', content)

    def test_offline_theme_matches_platform_default_tokens(self):
        stylesheet = Path(__file__).resolve().parents[5] / 'mango-console/src/styles/index.css'
        defaults = stylesheet.read_text().split('}', 1)[0]
        platform = dict(re.findall(r'(--m-[\w-]+):\s*(#[0-9a-fA-F]+)', defaults))
        offline = dict(re.findall(r'(--m-[\w-]+):\s*(#[0-9a-fA-F]+)', ReportHtmlService.styles()))
        self.assertGreaterEqual(len(offline), 20)
        for token, color in offline.items():
            self.assertEqual(color, platform[token], token)

    def test_report_layout_has_semantic_statuses_table_headers_and_no_external_assets(self):
        content = ReportHtmlService.render(sample_snapshot(), '示例平台').decode()
        self.assertIn('mango-platform-bar', content)
        self.assertIn('mango-tone-danger', content)
        self.assertIn('mango-tone-warning', content)
        self.assertIn('scope="col"', content)
        self.assertIn('mango-report-conclusion', content)
        self.assertIn('background:var(--m-table-header-bg)', content)
        self.assertNotRegex(content, r'<(?:script|link)\b[^>]*\bsrc=')
        self.assertIn("script-src 'sha256-", content)
        self.assertNotRegex(content, r'(?:src|href)="https?://')

    def test_report_domain_config_is_relocated_without_replacing_existing_key(self):
        from src.apps.system.services.configuration.system_config import get_config_definition_map
        definitions = get_config_definition_map()
        domain = definitions['SYSTEM_DOMAIN_NAME']
        self.assertEqual(domain.group, 'report_delivery')
        self.assertLess(domain.sort, definitions['REPORT_DELIVERY_CONFIG'].sort)

    def test_http_routes_keep_explicit_permissions_and_do_not_become_public(self):
        from django.urls import resolve
        from src.apps.user.middleware.permission import MenuActionPermission
        for path, method, permission in (
            ('/api/system/test/suite/offline', 'post', 'report:read'),
            ('/api/system/cache/data/report-delivery/metadata', 'get', 'system.settings:read'),
            ('/api/system/cache/data/report-delivery/sample', 'post', 'system.settings:change'),
        ):
            match = resolve(path)
            action = match.func.actions[method]
            self.assertEqual(permission_for_view(match.func.cls, action), permission)
            self.assertFalse(path.startswith(MenuActionPermission.PUBLIC_PATH_PREFIXES))

    def test_anonymous_and_out_of_scope_export_are_denied(self):
        with self.assertRaises(TestCenterError):
            OfflineReportSelector.require_permission(None)
        with patch('src.apps.test_center.selectors.offline_report.PermissionMenuService.is_effective_super_admin', return_value=False), \
             patch('src.apps.test_center.selectors.offline_report.PermissionMenuService.permission_keys_for_user', return_value={'report:read'}), \
             patch('src.apps.test_center.selectors.offline_report.ProjectProductScopeService.has_project_product', return_value=False):
            with self.assertRaises(TestCenterError):
                OfflineReportSelector.require_product(SimpleNamespace(id=1), 3)

    def test_disabled_preserves_existing_notifications_and_failure_can_fallback(self):
        notice = SimpleNamespace(mail=None, work_weixin=None, feishu='https://example.com/webhook', dingding=None)
        with patch.object(OfflineReportService, 'config', return_value=ReportDeliveryConfig()), patch.object(OfflineReportService, 'render') as render:
            self.assertIsNone(ReportDeliveryService.prepare(ReportSourceEnum.SUITE, 1, notice))
            render.assert_not_called()
        with patch.object(OfflineReportService, 'config', side_effect=RuntimeError('invalid config')):
            self.assertIsNone(ReportDeliveryService.prepare(ReportSourceEnum.SUITE, 1, notice))
        with patch.object(OfflineReportService, 'config', return_value=ReportDeliveryConfig(enabled=True)), \
             patch.object(OfflineReportService, 'render', side_effect=RuntimeError('private')):
            session = ReportDeliveryService.prepare(ReportSourceEnum.SUITE, 1, notice)
            self.assertIn('本次发送在线报告', session.note)
    def test_upload_failure_does_not_block_any_notification_channel(self):
        notice = SimpleNamespace(mail=['reader@example.com'], work_weixin='https://example.com/wechat', feishu='https://example.com/feishu', dingding='https://example.com/dingding')
        with patch.object(OfflineReportService, 'config', return_value=ReportDeliveryConfig(enabled=True)), \
             patch.object(OfflineReportService, 'render', return_value=('report.html', b'example')), \
             patch.object(OfflineReportService, 'upload_links', side_effect=RuntimeError('private')) as upload, \
             patch('src.apps.test_center.services.reporting.report_delivery.EmailSend') as mail, \
             patch('src.apps.test_center.services.reporting.report_delivery.WeChatSend') as wechat, \
             patch('src.apps.test_center.services.reporting.report_delivery.DingDingSend') as dingding, \
             patch('src.apps.test_center.services.reporting.report_delivery.FeiShuSend') as feishu:
            mail.return_value.build_test_report_html.return_value = 'example'
            wechat.return_value.build_test_report_markdown.return_value = 'example'
            dingding.return_value.build_test_report_markdown.return_value = 'example'
            feishu.return_value.build_test_report_card.side_effect = lambda: {'elements': []}
            session = ReportDeliveryService.prepare(ReportSourceEnum.SUITE, 1, notice)
            session.send(notice, '示例平台', 'https://example.com', lambda: {
                'send_user': 'sender@example.com', 'email_host': 'smtp.example.com', 'stamp_key': 'example'})
            upload.assert_called_once()
            self.assertIn('离线报告生成失败', mail.return_value.send_mail.call_args.args[1])
            self.assertIn('离线报告生成失败', wechat.return_value.send_markdown.call_args.args[0])
            self.assertEqual(feishu.return_value.send_interactive_card.call_count, 1)
            dingding.return_value.send_markdown.assert_called_once()
