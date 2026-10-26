import smtplib
import unittest
from unittest.mock import Mock, patch
import requests

from src.apps.system.exceptions import SystemError, SYSTEM_NOTICE_EMAIL_FAILED, SYSTEM_NOTICE_WEBHOOK_FAILED
from src.apps.system.schemas.notice import EmailNoticeModel, FeiShuNoticeModel, WeChatNoticeModel, DingDingNoticeModel
from src.apps.system.services.notice import EmailSend, FeiShuSend, WeChatSend, DingDingSend
from src.apps.user.services.credential import UserCredentialService
from src.apps.user.exceptions import UserError, USER_CREDENTIAL_EMAIL_CONFIG_FAILED


class NoticeTransportTests(unittest.TestCase):
    def test_senders_are_owned_by_platform_not_internal_package(self):
        for sender in (EmailSend, FeiShuSend, WeChatSend, DingDingSend):
            self.assertTrue(sender.__module__.startswith('src.apps.system.services.notice.'))

    def test_feishu_and_wechat_keep_distinct_protocols_and_timeouts(self):
        for cls, config, module, success, protocol in (
            (FeiShuSend, FeiShuNoticeModel, 'feishu', {'code': 0}, 'msg_type'),
            (WeChatSend, WeChatNoticeModel, 'wechat', {'errcode': 0}, 'msgtype'),
        ):
            with self.subTest(channel=module), patch(f'src.apps.system.services.notice.{module}.requests.post',
                    return_value=Mock(json=lambda: success)) as post:
                cls(config(webhook='https://example.com/webhook')).send_text('测试通知')
                payload = post.call_args.kwargs['json']
                self.assertEqual(payload[protocol], 'text')
                self.assertEqual(post.call_args.kwargs['timeout'], 10)
                if module == 'wechat':
                    self.assertEqual(payload['text']['mentioned_mobile_list'], [])
                    self.assertEqual(payload['text']['content'], '测试通知')

    def test_wechat_mentions_send_one_message_not_one_per_recipient(self):
        with patch('src.apps.system.services.notice.wechat.requests.post', return_value=Mock(json=lambda: {'errcode': 0})) as post:
            WeChatSend(WeChatNoticeModel(webhook='https://example.com/webhook')).send_text('测试通知', mentioned_mobile_list=['10000', '10001'])
        post.assert_called_once()
        self.assertEqual(post.call_args.kwargs['json']['text']['mentioned_mobile_list'], ['10000', '10001'])

    def test_webhook_error_uses_owned_safe_business_exception(self):
        for cls, config, module in (
            (FeiShuSend, FeiShuNoticeModel, 'feishu'),
            (WeChatSend, WeChatNoticeModel, 'wechat'),
            (DingDingSend, DingDingNoticeModel, 'dingding'),
        ):
            with self.subTest(channel=module), patch(f'src.apps.system.services.notice.{module}.requests.post',
                    return_value=Mock(json=lambda: {'code': 1, 'errcode': 1, 'msg': 'private-token'})):
                with self.assertRaises(SystemError) as caught:
                    cls(config(webhook='https://example.com/webhook')).send_text('测试通知')
                self.assertEqual(caught.exception.code, SYSTEM_NOTICE_WEBHOOK_FAILED.code)
                self.assertNotIn('private-token', str(caught.exception))

    def test_email_smtp_payload_and_authentication_failure(self):
        sender = EmailSend(EmailNoticeModel(send_user='sender@example.com', email_host='smtp.example.com',
                           stamp_key='example-password', send_list=['reader@example.com']))
        with patch('src.apps.system.services.notice.email.smtplib.SMTP') as smtp:
            sender.send_mail('测试通知', '<p>内容</p>', subtype='html')
        connection = smtp.return_value.__enter__.return_value
        connection.starttls.assert_called_once()
        connection.login.assert_called_once_with('sender@example.com', 'example-password')
        connection.sendmail.assert_called_once()
        with patch('src.apps.system.services.notice.email.smtplib.SMTP', side_effect=smtplib.SMTPAuthenticationError(535, b'private-password')):
            with self.assertRaises(SystemError) as caught:
                sender.send_mail('测试通知', '内容')
        self.assertEqual(caught.exception.code, SYSTEM_NOTICE_EMAIL_FAILED.code)
        self.assertNotIn('private-password', str(caught.exception))

    def test_credential_email_uses_platform_sender_and_preserves_user_error_boundary(self):
        with patch.object(UserCredentialService, '_mail_config', return_value=('sender@example.com', 'smtp.example.com', 'example-password')), \
             patch('src.apps.user.services.credential.SystemConfigService.get_platform_name', return_value='示例平台'), \
             patch('src.apps.user.services.credential.EmailSend') as sender:
            UserCredentialService.send_email(email='reader@example.com', subject='验证码', content='示例验证码')
            sender.return_value.send_mail.assert_called_once_with('验证码', '示例验证码', subtype='html')
            sender.return_value.send_mail.side_effect = SystemError(SYSTEM_NOTICE_EMAIL_FAILED)
            with self.assertRaises(UserError) as caught:
                UserCredentialService.send_email(email='reader@example.com', subject='验证码', content='示例验证码')
        self.assertEqual(caught.exception.code, USER_CREDENTIAL_EMAIL_CONFIG_FAILED.code)

    def test_webhook_network_and_non_json_errors_are_safe(self):
        for cls, config, module in (
            (FeiShuSend, FeiShuNoticeModel, 'feishu'),
            (WeChatSend, WeChatNoticeModel, 'wechat'),
            (DingDingSend, DingDingNoticeModel, 'dingding'),
        ):
            for result in (requests.Timeout('private-token'), Mock(json=Mock(side_effect=ValueError('private-body')))):
                kwargs = {'side_effect': result} if isinstance(result, Exception) else {'return_value': result}
                with self.subTest(channel=module), patch(f'src.apps.system.services.notice.{module}.requests.post', **kwargs):
                    with self.assertRaises(SystemError) as caught:
                        cls(config(webhook='https://example.com/webhook')).send_text('测试通知')
                    self.assertNotIn('private', str(caught.exception))
