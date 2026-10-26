# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 企微通知封装
# @Time   : 2022-11-04 22:05
# @Author : 毛鹏

import requests

from src.apps.system.exceptions import SystemError, SYSTEM_NOTICE_WEBHOOK_FAILED, SYSTEM_NOTICE_FILE_FAILED
from src.apps.system.schemas.notice import WeChatNoticeModel, TestReportModel
from .failure_details import ReportFailureRenderer


class WeChatSend:
    def __init__(self,
                 notice_config: WeChatNoticeModel,
                 test_report: TestReportModel | None = None,
                 domain_name: str = None,
                 content: str = None, platform_name: str = '芒果测试平台'):
        self.notice_config = notice_config
        self.test_report = test_report
        self.domain_name = domain_name
        self.content = content
        self.platform_name = platform_name
        self.headers = {"Content-Type": "application/json"}

    def send_wechat_notification(self):
        if self.content is None:
            content = self.build_test_report_markdown()
        else:
            content = self.content
        self.send_markdown(content)

    def build_test_report_markdown(self, include_failure_details=True):
        if self.test_report is None:
            raise SystemError(SYSTEM_NOTICE_WEBHOOK_FAILED)

        report = self.test_report
        failed = self._safe_int(report.fail)
        warning = self._safe_int(report.warning)
        warning_note = "（非测试人员可忽略告警用例）" if warning > 0 else ""
        total = self._safe_int(report.case_sum)
        success = self._safe_int(report.success)
        success_rate = self._format_rate(report.success_rate)
        status_text = "通过" if failed == 0 else "失败"
        status_color = "info" if failed == 0 else "warning"
        metric_color = "info" if failed == 0 else "warning"
        fail_color = "comment" if failed == 0 else "warning"
        project_product = report.project_name
        if report.product_name:
            project_product = f"{report.project_name} / {report.product_name}"

        lines = [
            f"## {'✅' if failed == 0 else '❌'}{self.platform_name}自动化测试报告 - <font color=\"{status_color}\">{status_text}</font>",
            f"**项目产品：** {project_product}",
            f"**测试环境：** {report.test_environment}",
            f"**任务名称：** {report.task_name or '-'}",
            f"**测试套ID：** {report.test_suite_id or '-'}",
            ">",
            f"**成功率：** <font color=\"{metric_color}\">{success_rate}%</font>",
            f"**总用例：** {total}",
            f"**成功：** <font color=\"info\">{success}</font>",
            f"**失败：** <font color=\"{fail_color}\">{failed}</font>",
        ]

        category_lines = self._build_category_lines()
        if category_lines:
            lines.append(">")
            lines.extend(category_lines)

        lines.extend([
            ">",
            f"**告警用例：** <font color=\"warning\">{warning}</font>{warning_note}",
            f"**已排除用例：** {report.excluded_count}",
            f"**执行耗时：** {report.execution_duration}",
            f"**开始时间：** <font color=\"comment\">{report.test_time}</font>",
            "非相关负责人员可忽略此消息。",
        ])

        if self.domain_name:
            lines.extend([">", f"[查看测试报告]({self.domain_name})"])

        content = "\n".join(lines)
        return ReportFailureRenderer.markdown(content, report.failure_details, report.failure_details_note) if include_failure_details else content

    def send_markdown(self, content):
        self._send({'msgtype': 'markdown', 'markdown': {'content': content}})

    def _send(self, payload):
        try:
            res = requests.post(
                url=self.notice_config.webhook, json=payload, headers=self.headers,
                proxies={'http': None, 'https': None}, timeout=10,
            )
            result = res.json()
            if not isinstance(result, dict) or result.get('errcode') != 0:
                raise SystemError(SYSTEM_NOTICE_WEBHOOK_FAILED)
        except (requests.RequestException, ValueError):
            raise SystemError(SYSTEM_NOTICE_WEBHOOK_FAILED) from None

    def send_file_msg(self, file):
        res = requests.post(
            url=self.notice_config.webhook,
            json={"msgtype": "file", "file": {"media_id": self.__upload_file(file)}},
            headers=self.headers,
            proxies={'http': None, 'https': None}, timeout=10
        )
        if res.json()['errcode'] != 0:
            raise SystemError(SYSTEM_NOTICE_FILE_FAILED)

    def __upload_file(self, file):
        with open(file, 'rb') as content:
            res = requests.post(
                url=self.notice_config.webhook,
                files={'file': content},
                proxies={'http': None, 'https': None}, timeout=10,
            ).json()
        return res['media_id']

    @staticmethod
    def _format_rate(value):
        if value is None:
            return "0"
        return f"{float(value):.2f}".rstrip("0").rstrip(".")

    @staticmethod
    def _safe_int(value):
        return int(value or 0)

    def _build_category_lines(self):
        report = self.test_report
        categories = [
            ("接口", report.api_case_sum, report.api_fail),
            ("UI", report.ui_case_sum, report.ui_fail),
            ("单元", report.pytest_case_sum, report.pytest_fail),
        ]
        lines = []
        for name, case_sum, fail_sum in categories:
            if case_sum is not None and case_sum > 0:
                fail_sum = self._safe_int(fail_sum)
                fail_color = "comment" if fail_sum == 0 else "warning"
                lines.append(
                    f"**{name}用例：** {case_sum} 个，失败 <font color=\"{fail_color}\">{fail_sum}</font> 个"
                )
        return lines

    def send_text(self, content, mentioned_list=None, mentioned_mobile_list=None):
        for values in (mentioned_list, mentioned_mobile_list):
            if values is not None and (not isinstance(values, list) or any(not isinstance(item, str) for item in values)):
                raise SystemError(SYSTEM_NOTICE_WEBHOOK_FAILED)
        self._send({'msgtype': 'text', 'text': {'content': content,
                   'mentioned_list': mentioned_list or [], 'mentioned_mobile_list': mentioned_mobile_list or []}})
