import json
import unittest
from unittest.mock import patch, Mock

from mangotools.enums import TestCaseTypeEnum
from src.apps.system.schemas.notice import ReportFailureModel, DingDingNoticeModel
from src.apps.system.services.notice import ReportFailureRenderer, DingDingSend


class NoticeFailureDetailTests(unittest.TestCase):
    def rows(self, count=7):
        return [ReportFailureModel(case_type=TestCaseTypeEnum.API, case_name=f'用例{i}',
                    target_name=f'接口{i}', message='断言失败') for i in range(count)]

    def test_feishu_uses_native_pages_and_keeps_every_row_within_budget(self):
        rows = self.rows() + [ReportFailureModel(case_type=TestCaseTypeEnum.UI, case_name='登录', target_name='点击登录', message='元素不存在'),
                ReportFailureModel(case_type=TestCaseTypeEnum.PYTEST, case_name='代码测试', target_name='example.py::test_example', message='AssertionError')]
        card = ReportFailureRenderer.feishu({'elements': []}, rows)
        tables = [item for item in card['elements'] if item['tag'] == 'table']
        self.assertEqual(len(tables), 3)
        self.assertTrue(all(table['page_size'] == 5 for table in tables))
        self.assertEqual(len(tables[0]['rows']), 7)
        self.assertEqual(tables[0]['rows'][-1]['failure_target'], '接口6')
        self.assertEqual(tables[1]['columns'][1]['display_name'], '失败步骤')
        self.assertEqual(tables[2]['columns'][1]['display_name'], '测试标识')
        self.assertNotIn('callback', json.dumps(card))

    def test_feishu_budgets_actual_ascii_json_and_announces_omitted_rows(self):
        rows = self.rows(200)
        for row in rows:
            row.message = '长错误提示' * 100
        card = ReportFailureRenderer.feishu({'elements': []}, rows)
        card['elements'].append({'tag': 'div', 'text': {'tag': 'plain_text', 'content': '链接附加信息' * 500}})
        ReportFailureRenderer.fit_feishu(card)
        self.assertLessEqual(len(json.dumps({'msg_type': 'interactive', 'card': card}).encode()), 20*1024)
        self.assertIn('完整报告', json.dumps(card, ensure_ascii=False))

    def test_email_has_every_failure_row_and_escapes_untrusted_content(self):
        rows = self.rows(150)
        rows[-1].message = '<script>alert(1)</script>'
        content = ReportFailureRenderer.email(rows)
        self.assertIn('用例149', content)
        self.assertNotIn('<script>', content)
        self.assertIn('&lt;script&gt;', content)
        self.assertEqual(content.count('<tr>'), 151)

    def test_wechat_is_a_bounded_preview_not_fake_pagination(self):
        content = ReportFailureRenderer.markdown('报告摘要', self.rows(10))
        self.assertIn('5/10', content)
        self.assertLessEqual(len(content.encode()), 4096)
        self.assertNotIn('callback', content)

    def test_dingding_uses_native_markdown_payload_not_feishu_card(self):
        sender = DingDingSend(DingDingNoticeModel(webhook='https://example.com/webhook'))
        with patch('src.apps.system.services.notice.dingding.requests.post', return_value=Mock(json=lambda: {'errcode': 0})) as post:
            sender.send_markdown('## ❌示例报告\n<font color="warning">失败</font>')
        payload = post.call_args.kwargs['json']
        self.assertEqual(payload['msgtype'], 'markdown')
        self.assertEqual(payload['markdown']['title'], '❌示例报告')
        self.assertNotIn('<font', payload['markdown']['text'])
        self.assertNotIn('card', payload)
