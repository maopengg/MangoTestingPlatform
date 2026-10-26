import unittest
from unittest.mock import patch

from src.apps.system.schemas.notice import EmailNoticeModel, FeiShuNoticeModel, TestReportModel, WeChatNoticeModel
from src.apps.system.services.notice import EmailSend, FeiShuSend, WeChatSend


class NoticeTitleTests(unittest.TestCase):
    def report(self, failed):
        return TestReportModel(
            test_suite_id=1, task_name='示例任务', project_name='示例项目', product_name='示例产品',
            test_environment='测试环境', case_sum=2, success=2-failed, fail=failed, warning=0,
            success_rate=100 if failed == 0 else 50, api_case_sum=2, api_fail=failed,
            ui_case_sum=0, ui_fail=0, pytest_case_sum=0, pytest_fail=0,
            execution_duration='1秒', test_time='2026-10-26 10:00:00',
        )

    def test_all_report_channels_prefix_titles_with_the_actual_result(self):
        for failed, icon, result in ((0, '✅', '通过'), (1, '❌', '失败')):
            with self.subTest(failed=failed):
                report = self.report(failed)
                title = f'{icon}示例平台自动化测试报告 - {result}'
                mail = EmailSend(EmailNoticeModel(send_user='sender@example.com', email_host='smtp.example.com',
                    stamp_key='example', send_list=['reader@example.com']), report, platform_name='示例平台')
                feishu = FeiShuSend(FeiShuNoticeModel(webhook='https://example.com/webhook'), report, platform_name='示例平台')
                wechat = WeChatSend(WeChatNoticeModel(webhook='https://example.com/webhook'), report, platform_name='示例平台')
                self.assertEqual(feishu.build_test_report_card()['header']['title']['content'], title)
                self.assertTrue(wechat.build_test_report_markdown().startswith(f'## {icon}示例平台自动化测试报告 - '))
                self.assertEqual(mail.build_test_report_title(), title)
                self.assertIn(title, mail.build_test_report_html())
                with patch.object(mail, 'send_mail') as send:
                    mail.send_main()
                self.assertEqual(send.call_args.args[0], title)

    def test_non_report_mail_is_not_given_a_result_icon(self):
        mail = EmailSend(EmailNoticeModel(send_user='sender@example.com', email_host='smtp.example.com',
            stamp_key='example', send_list=['reader@example.com']), content='普通通知')
        with patch.object(mail, 'send_mail') as send:
            mail.send_main()
        self.assertEqual(send.call_args.args[0], '测试报告通知')

    def test_feishu_report_uses_compact_summary_without_metric_tiles(self):
        card = FeiShuSend(FeiShuNoticeModel(webhook='https://example.com/webhook'), self.report(1)).build_test_report_card()
        self.assertFalse(card['config']['wide_screen_mode'])
        self.assertFalse(any(item['tag'] == 'column_set' for item in card['elements']))
        content = '\n'.join(item.get('text', {}).get('content', '') for item in card['elements'])
        self.assertIn('成功率', content)
        self.assertIn('总用例', content)
        self.assertIn('已排除', content)
        self.assertIn('开始时间', content)

    def test_feishu_metadata_order_and_single_line_statistics(self):
        report = self.report(1)
        card = FeiShuSend(FeiShuNoticeModel(webhook='https://example.com/webhook'), report).build_test_report_card()
        metadata = card['elements'][0]['text']['content'].splitlines()
        self.assertEqual(metadata[0], f'**项目产品：** {report.project_name} / {report.product_name}')
        self.assertEqual(metadata[1], f'**测试环境：** {report.test_environment}')
        self.assertEqual(metadata[3], f'**执行报告ID：** {report.test_suite_id}')
        self.assertEqual(metadata[4], f'**开始时间：** {report.test_time} · **耗时：** {report.execution_duration}')
        stats = card['elements'][1]['text']['content']
        self.assertNotIn('\n', stats)
        for label in ('成功率', '总用例', '成功', '失败', '告警用例', '已排除用例'):
            self.assertIn(f'**{label}：**', stats)
        self.assertIn('总用例：** 2 个', stats)
        self.assertNotIn('耗时', stats)
