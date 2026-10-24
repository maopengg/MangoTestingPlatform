from unittest.mock import patch

from django.test import SimpleTestCase
from mangotools.models import EmailNoticeModel, FeiShuNoticeModel, TestReportModel, WeChatNoticeModel
from mangotools.notice import EmailSend, FeiShuSend, WeChatSend

from src.apps.system.models import CacheData
from src.apps.system.services.system_config import SystemConfigService
from src.apps.user.services.credential import UserCredentialService


class PlatformBrandingTests(SimpleTestCase):
    @patch('src.apps.system.services.system_config.CacheData.objects.get', side_effect=CacheData.DoesNotExist)
    def test_unconfigured_names_use_registered_defaults(self, _get):
        self.assertEqual(SystemConfigService.get_platform_branding(), {
            'platform_name': '芒果测试平台', 'platform_name_en': 'mango-test-platform',
        })

    @patch.object(SystemConfigService, 'get')
    def test_names_are_trimmed_and_empty_historical_values_fall_back(self, get):
        get.side_effect = [' 演示平台 ', ' ExamplePlatform ']
        self.assertEqual(SystemConfigService.get_platform_branding(), {
            'platform_name': '演示平台', 'platform_name_en': 'ExamplePlatform',
        })
        get.side_effect = [' ', None]
        self.assertEqual(SystemConfigService.get_platform_name(), '芒果测试平台')

    def test_names_reject_empty_excessively_long_and_control_characters(self):
        for key in ('PLATFORM_NAME', 'PLATFORM_NAME_EN'):
            self.assertIsNone(SystemConfigService.validate_editable_config(key, '演示平台'))
            for value in ('', ' ', 'x' * 65, 'Title\r\nInjected', 'Title\x00'):
                with self.subTest(key=key, value=repr(value)):
                    self.assertIsNotNone(SystemConfigService.validate_editable_config(key, value))

    def test_notice_renderers_use_custom_name_and_escape_email_html(self):
        report = TestReportModel(
            project_name='示例项目', test_environment='测试环境', case_sum=1,
            success=1, success_rate=100, fail=0, execution_duration='00:00:01', test_time='2026-10-25',
        )
        name = '演示<&>平台'
        email = EmailSend(EmailNoticeModel(
            send_user='sender@example.com', email_host='smtp.example.com', stamp_key='test', send_list=[],
        ), report, platform_name=name)
        self.assertIn('演示&lt;&amp;&gt;平台自动化测试报告', email.build_test_report_html())
        feishu = FeiShuSend(FeiShuNoticeModel(webhook='https://example.com/hook'), report, platform_name=name)
        self.assertIn(name, feishu.build_test_report_card()['header']['title']['content'])
        wechat = WeChatSend(WeChatNoticeModel(webhook='https://example.com/hook'), report, platform_name=name)
        self.assertIn(name, wechat.build_test_report_markdown())

    @patch.object(SystemConfigService, 'get_platform_name', return_value='演示<&>平台')
    @patch.object(UserCredentialService, 'send_email')
    def test_credential_email_uses_configured_name_without_html_injection(self, send, _name):
        UserCredentialService.send_password(email='user@example.com', name='User', password='ExamplePassword', action='注册')
        self.assertEqual(send.call_args.kwargs['subject'], '演示<&>平台注册')
        self.assertIn('演示&lt;&amp;&gt;平台注册', send.call_args.kwargs['content'])
