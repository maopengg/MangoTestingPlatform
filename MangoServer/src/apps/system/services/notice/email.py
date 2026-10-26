# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 邮箱通知封装
# @Time   : 2022-11-04 22:05
# @Author : 毛鹏
import html
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from .failure_details import ReportFailureRenderer

from src.apps.system.exceptions import SystemError, SYSTEM_NOTICE_EMAIL_FAILED
from src.apps.system.schemas.notice import EmailNoticeModel, TestReportModel

from email.utils import formataddr

class EmailSend:

    def __init__(self, notice_config: EmailNoticeModel, test_report: TestReportModel = None, domain_name: str = None,
                 content: str = None, platform_name: str = '芒果测试平台'):
        self.test_report = test_report
        self.notice_config = notice_config
        self.domain_name = domain_name
        self.content = content
        self.platform_name = platform_name

    def send_main(self) -> None:
        if self.content is None:
            content = self.build_test_report_html()
            self.send_mail(self.build_test_report_title(), content, subtype='html')
        else:
            content = self.content
            self.send_mail('测试报告通知', content)

    def build_test_report_title(self) -> str:
        failed = self._safe_int(self.test_report.fail)
        return f"{'✅' if failed == 0 else '❌'}{self.platform_name}自动化测试报告 - {'通过' if failed == 0 else '失败'}"

    def build_test_report_html(self) -> str:
        report = self.test_report
        project_product = report.project_name
        if report.product_name:
            project_product = f"{report.project_name} / {report.product_name}"

        failed = self._safe_int(report.fail)
        warning = self._safe_int(report.warning)
        warning_note = "（非测试人员可忽略告警用例）" if warning > 0 else ""
        total = self._safe_int(report.case_sum)
        success = self._safe_int(report.success)
        status_text = "通过" if failed == 0 else "失败"
        status_color = "#00B42A" if failed == 0 else "#F53F3F"
        status_bg = "#E8FFEA" if failed == 0 else "#FFECE8"
        status_border = "#B7EB8F" if failed == 0 else "#FFCCC7"
        success_rate = self._format_rate(report.success_rate)
        progress_width = max(0, min(100, float(report.success_rate or 0)))

        category_rows = "".join(
            self._category_row(name, case_sum, fail_sum)
            for name, case_sum, fail_sum in [
                ("接口", report.api_case_sum, report.api_fail),
                ("UI", report.ui_case_sum, report.ui_fail),
                ("单元", report.pytest_case_sum, report.pytest_fail),
            ]
            if case_sum is not None and case_sum > 0
        )
        category_section = ""
        if category_rows:
            category_section = f"""
                <tr>
                    <td style="padding: 0 18px 14px;">
                        {self._section_title('用例分布', '按测试类型汇总执行规模和失败数量')}
                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse: collapse; border: 1px solid #E5E6EB; border-radius: 6px; overflow: hidden;">
                            <tr>
                                <th align="left" style="padding: 9px 12px; background: #F7F8FA; color: #4E5969; font-size: 12px; font-weight: 600;">类型</th>
                                <th align="right" style="padding: 9px 12px; background: #F7F8FA; color: #4E5969; font-size: 12px; font-weight: 600;">用例数</th>
                                <th align="right" style="padding: 9px 12px; background: #F7F8FA; color: #4E5969; font-size: 12px; font-weight: 600;">失败数</th>
                            </tr>
                            {category_rows}
                        </table>
                    </td>
                </tr>
            """

        report_link = ""
        if self.domain_name:
            report_link = f"""
                <tr>
                    <td style="padding: 2px 18px 18px;">
                        <a href="{self._escape(self.domain_name)}" style="display: inline-block; padding: 8px 14px; background: #165DFF; color: #FFFFFF; text-decoration: none; border-radius: 4px; font-size: 13px; font-weight: 600;">查看完整测试报告</a>
                    </td>
                </tr>
            """

        return f"""<!doctype html>
<html>
<body style="margin: 0; padding: 0; background: #F2F3F5; color: #1D2129; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background: #F2F3F5; padding: 18px 0;">
        <tr>
            <td align="center">
                <table role="presentation" width="720" cellpadding="0" cellspacing="0" style="width: 720px; max-width: 94%; background: #FFFFFF; border: 1px solid #E5E6EB; border-radius: 8px; overflow: hidden;">
                    <tr>
                        <td style="padding: 14px 18px; border-bottom: 1px solid #E5E6EB; background: #FFFFFF;">
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse: collapse;">
                                <tr>
                                    <td valign="middle">
                                        <div style="color: #1D2129; font-size: 18px; line-height: 26px; font-weight: 700;">{self._escape(self.build_test_report_title())}</div>
                                        <div style="margin-top: 3px; color: #86909C; font-size: 12px; line-height: 18px;">{self._escape(project_product)} · {self._escape(report.test_environment)}</div>
                                    </td>
                                    <td align="right" valign="middle" style="padding-left: 12px;">
                                        <span style="display: inline-block; padding: 4px 9px; border: 1px solid {status_border}; border-radius: 4px; background: {status_bg}; color: {status_color}; font-size: 12px; font-weight: 600;">{status_text}</span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 14px 18px 4px;">
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse: separate; border-spacing: 8px 0;">
                                <tr>
                                    {self._summary_cell('成功率', f'{success_rate}%', status_color)}
                                    {self._summary_cell('总用例', total, '#1D2129')}
                                    {self._summary_cell('成功', success, '#00B42A')}
                                    {self._summary_cell('失败', failed, '#F53F3F')}
                                    {self._summary_cell('告警', f'{warning}{warning_note}', '#FF7D00')}
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 18px 14px;">
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border: 1px solid #E5E6EB; border-radius: 8px; background: #F7F8FA;">
                                <tr>
                                    <td style="padding: 12px 14px;">
                                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                                            <tr>
                                                <td valign="top" width="50%" style="padding-right: 8px;">
                                                    {self._detail_block('任务名称', report.task_name or '-')}
                                                </td>
                                                <td valign="top" width="25%" style="padding: 0 8px;">
                                                    {self._detail_block('测试套ID', report.test_suite_id or '-')}
                                                </td>
                                                <td valign="top" width="25%" style="padding-left: 8px;">
                                                    {self._detail_block('开始时间', report.test_time)}
                                                </td>
                                            </tr>
                                        </table>
                                        <div style="margin-top: 12px;">
                                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                                                <tr>
                                                    <td style="color: #4E5969; font-size: 12px;">通过进度</td>
                                                    <td align="right" style="color: #86909C; font-size: 12px;">{self._escape(success)} / {self._escape(total)}</td>
                                                </tr>
                                            </table>
                                            <div style="margin-top: 7px; height: 7px; background: #E5E6EB; border-radius: 999px; overflow: hidden;">
                                                <div style="width: {progress_width}%; height: 7px; background: {status_color}; border-radius: 999px; line-height: 7px; font-size: 7px;">&nbsp;</div>
                                            </div>
                                        </div>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    {category_section}
                    <tr>
                        <td style="padding: 0 18px 14px;">
                            {self._section_title('执行信息', '测试任务运行摘要')}
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border: 1px solid #E5E6EB; border-radius: 6px; background: #FFFFFF;">
                                <tr>
                                    <td width="50%" style="padding: 10px 12px; color: #4E5969; font-size: 13px; border-right: 1px solid #E5E6EB;">
                                        已排除用例：<strong>{report.excluded_count}</strong><br>
                                        执行耗时：<strong style="color: #1D2129;">{self._escape(report.execution_duration)}</strong>
                                    </td>
                                    <td width="50%" style="padding: 10px 12px; color: #4E5969; font-size: 13px;">
                                        测试环境：<strong style="color: #1D2129;">{self._escape(report.test_environment)}</strong>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    {report_link}
                    <tr>
                        <td style="padding: 12px 18px; background: #F7F8FA; color: #86909C; font-size: 12px; line-height: 18px; border-top: 1px solid #E5E6EB;">
                            详细情况可前往芒果自动化平台查看，非相关负责人员可忽略此消息。
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
{ReportFailureRenderer.email(report.failure_details, report.failure_details_note)}
</body>
</html>"""

    def send_mail(self, sub: str, content: str, subtype: str = 'plain') -> None:
        try:
            msg = MIMEMultipart()
            msg['From'] = formataddr((self.platform_name, self.notice_config.send_user))
            msg['To'] = ";".join(self.notice_config.send_list)
            msg['Subject'] = sub
            msg.attach(MIMEText(content, subtype, 'utf-8'))
            with smtplib.SMTP(self.notice_config.email_host, timeout=10) as server:
                server.starttls()
                server.login(self.notice_config.send_user, self.notice_config.stamp_key)
                server.sendmail(self.notice_config.send_user, self.notice_config.send_list, msg.as_string())
                server.quit()
        except (OSError, smtplib.SMTPException):
            raise SystemError(SYSTEM_NOTICE_EMAIL_FAILED) from None

    @staticmethod
    def _format_rate(value):
        if value is None:
            return "0"
        return f"{float(value):.2f}".rstrip("0").rstrip(".")

    @staticmethod
    def _safe_int(value):
        return int(value or 0)

    @staticmethod
    def _escape(value):
        return html.escape(str(value), quote=True)

    def _detail_block(self, label, value):
        return f"""
            <div style="min-height: 44px;">
                <div style="color: #86909C; font-size: 12px; line-height: 18px;">{self._escape(label)}</div>
                <div style="margin-top: 2px; color: #1D2129; font-size: 13px; line-height: 20px; font-weight: 600;">{self._escape(value)}</div>
            </div>
        """

    def _summary_cell(self, label, value, color):
        return f"""
            <td align="left" style="padding: 12px 12px; background: #FFFFFF; border: 1px solid #E5E6EB; border-radius: 6px;">
                <div style="color: #86909C; font-size: 12px; line-height: 18px;">{self._escape(label)}</div>
                <div style="margin-top: 4px; color: {color}; font-size: 22px; line-height: 26px; font-weight: 700;">{self._escape(value)}</div>
            </td>
        """

    def _section_title(self, title, desc):
        return f"""
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin: 0 0 8px;">
                <tr>
                    <td style="color: #1D2129; font-size: 14px; line-height: 22px; font-weight: 600;">{self._escape(title)}</td>
                    <td align="right" style="color: #86909C; font-size: 12px; line-height: 18px;">{self._escape(desc)}</td>
                </tr>
            </table>
        """

    def _category_row(self, name, case_sum, fail_sum):
        fail_sum = self._safe_int(fail_sum)
        fail_color = "#00B42A" if fail_sum == 0 else "#F53F3F"
        return f"""
            <tr>
                <td style="padding: 10px 12px; border-top: 1px solid #E5E6EB; color: #1D2129; font-size: 13px;">{self._escape(name)}</td>
                <td align="right" style="padding: 10px 12px; border-top: 1px solid #E5E6EB; color: #4E5969; font-size: 13px;">{self._escape(case_sum)}</td>
                <td align="right" style="padding: 10px 12px; border-top: 1px solid #E5E6EB; color: {fail_color}; font-size: 13px; font-weight: 600;">{self._escape(fail_sum)}</td>
            </tr>
        """
