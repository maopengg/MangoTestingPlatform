# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 飞书通知封装
# @Time   : 2025-12-10 18:30
# @Author : Qwen
import json

import requests

from src.apps.system.exceptions import SystemError, SYSTEM_NOTICE_WEBHOOK_FAILED
from src.apps.system.schemas.notice import FeiShuNoticeModel, TestReportModel
from .failure_details import ReportFailureRenderer


class FeiShuSend:
    def __init__(self,
                 notice_config: FeiShuNoticeModel,
                 test_report: TestReportModel | None = None,
                 domain_name: str = None,
                 content: str = None, platform_name: str = '芒果测试平台'):
        self.notice_config = notice_config
        self.test_report = test_report
        self.domain_name = domain_name
        self.content = content
        self.platform_name = platform_name
        self.headers = {"Content-Type": "application/json"}

    def send_feishu_notification(self):
        if self.content is not None:
            self.send_text(self.content)
            return
        self.send_test_report_card()

    def send_test_report_card(self):
        """
        发送飞书交互式卡片测试报告。
        """
        self.send_interactive_card(self.build_test_report_card())

    def build_test_report_card(self):
        """
        构建飞书机器人 webhook 可发送的 interactive card。
        """
        if self.test_report is None:
            raise SystemError(SYSTEM_NOTICE_WEBHOOK_FAILED)

        report = self.test_report
        success_rate = self._format_rate(report.success_rate)
        failed = self._safe_int(report.fail)
        warning = self._safe_int(report.warning)
        total = self._safe_int(report.case_sum)
        success = self._safe_int(report.success)
        header_template = "green" if failed == 0 else "red"
        status_text = "通过" if failed == 0 else "失败"
        project_product = report.project_name
        if report.product_name:
            project_product = f"{report.project_name} / {report.product_name}"

        elements = [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": (
                        f"**项目产品：** {project_product}\n"
                        f"**测试环境：** {report.test_environment}\n"
                        f"**任务名称：** {report.task_name or '-'}\n"
                        f"**执行报告ID：** {report.test_suite_id or '-'}\n"
                        f"**开始时间：** {report.test_time} · **耗时：** {report.execution_duration}"
                    )
                }
            },
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": (
                    f"**成功率：** {success_rate}%　|　**总用例：** {total} 个　|　"
                    f"**成功：** <font color='green'>{success} 个</font>　|　**失败：** <font color='red'>{failed} 个</font>　|　"
                    f"**告警用例：** {warning} 个　|　**已排除用例：** {report.excluded_count} 个"
                )}
            },
        ]

        category_lines = self._build_category_lines()
        if category_lines:
            elements.extend([
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "\n".join(category_lines)
                    }
                }
            ])

        if self.domain_name:
            elements.append({
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {
                            "tag": "plain_text",
                            "content": "查看测试报告"
                        },
                        "type": "primary",
                        "url": self.domain_name
                    }
                ]
            })

        return ReportFailureRenderer.feishu({
            "config": {
                "wide_screen_mode": False,
                "enable_forward": True
            },
            "header": {
                "template": header_template,
                "title": {
                    "tag": "plain_text",
                    "content": f"{'✅' if failed == 0 else '❌'}{self.platform_name}自动化测试报告 - {status_text}"
                }
            },
            "elements": elements
        }, report.failure_details, report.failure_details_note)

    def send_markdown(self, content):
        self._post_payload({
            "msg_type": "post",
            "content": {
                "post": {
                    "zh_cn": {
                        "title": f"{self.platform_name}测试报告",
                        "content": [[
                            {
                                "tag": "text",
                                "text": content
                            }
                        ]]
                    }
                }
            }
        })

    def send_text(self, content):
        """
        发送纯文本消息

        参数:
            content (str): 文本内容
        """
        self._post_payload({
            "msg_type": "text",
            "content": {
                "text": content
            }
        })

    def send_post(self, title, content_list):
        """
        发送富文本消息

        参数:
            title (str): 标题
            content_list (list): 内容列表，每个元素是一个包含tag的字典
        """
        self._post_payload({
            "msg_type": "post",
            "content": {
                "post": {
                    "zh_cn": {
                        "title": title,
                        "content": [content_list]
                    }
                }
            }
        })

    def send_interactive_card(self, card):
        """
        发送飞书交互式卡片消息。

        参数:
            card (dict): 飞书卡片 JSON。
        """
        self._post_payload({
            "msg_type": "interactive",
            "card": card
        })

    def _post_payload(self, payload):
        if payload.get('msg_type') == 'interactive':
            ReportFailureRenderer.fit_feishu(payload['card'])
        try:
            res = requests.post(
                url=self.notice_config.webhook,
                json=payload,
                headers=self.headers,
                proxies={'http': None, 'https': None}, timeout=10,
            )
            result = res.json()
            if not isinstance(result, dict) or (result.get("code") != 0 and result.get("StatusCode") != 0):
                raise SystemError(SYSTEM_NOTICE_WEBHOOK_FAILED)
        except (requests.RequestException, ValueError):
            raise SystemError(SYSTEM_NOTICE_WEBHOOK_FAILED) from None

    @staticmethod
    def _format_rate(value):
        if value is None:
            return "0"
        return f"{float(value):.2f}".rstrip("0").rstrip(".")

    @staticmethod
    def _safe_int(value):
        return int(value or 0)

    @staticmethod
    def _metric_column(label, value, color):
        return {
            "tag": "column",
            "width": "weighted",
            "weight": 1,
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**{label}**\n<font color='{color}'>{value}</font>"
                    }
                }
            ]
        }

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
                lines.append(
                    f"**{name}用例：** {case_sum} 个，失败 {self._safe_int(fail_sum)} 个"
                )
        return lines
