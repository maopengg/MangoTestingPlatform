import re

import requests

from src.apps.system.exceptions import SystemError, SYSTEM_NOTICE_WEBHOOK_FAILED
from src.apps.system.schemas.notice import DingDingNoticeModel, TestReportModel
from .wechat import WeChatSend


class DingDingSend(WeChatSend):
    def __init__(self, notice_config: DingDingNoticeModel, test_report: TestReportModel | None = None,
                 domain_name=None, content=None, platform_name='芒果测试平台'):
        super().__init__(notice_config, test_report, domain_name, content, platform_name)

    @staticmethod
    def plain_markdown(content):
        return re.sub(r'</?font\b[^>]*>', '', content)

    def build_test_report_markdown(self, include_failure_details=True):
        return self.plain_markdown(super().build_test_report_markdown(include_failure_details))

    def send_dingding_notification(self):
        self.send_markdown(self.content if self.content is not None else self.build_test_report_markdown())

    def send_markdown(self, content):
        content = self.plain_markdown(content)
        title = content.splitlines()[0].lstrip('# ').strip() if content else '测试报告通知'
        self._send({'msgtype': 'markdown', 'markdown': {'title': title, 'text': content}})

    def send_text(self, content):
        self._send({'msgtype': 'text', 'text': {'content': content}})

    def _send(self, payload):
        try:
            response = requests.post(self.notice_config.webhook, json=payload, headers=self.headers,
                                     proxies={'http': None, 'https': None}, timeout=10)
            result = response.json()
        except (requests.RequestException, ValueError):
            raise SystemError(SYSTEM_NOTICE_WEBHOOK_FAILED) from None
        if not isinstance(result, dict) or result.get('errcode') != 0:
            raise SystemError(SYSTEM_NOTICE_WEBHOOK_FAILED)
