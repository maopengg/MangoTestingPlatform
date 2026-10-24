import html
from dataclasses import dataclass, field


@dataclass(frozen=True)
class TaskGroupChildReport:
    task_name: str
    result: str
    test_suite_id: int | None = None
    case_sum: int = 0
    success: int = 0
    fail: int = 0
    warning: int = 0


@dataclass(frozen=True)
class TaskGroupNoticeReport:
    execution_id: int | None
    task_group_name: str
    project_name: str
    product_name: str
    test_environment: str
    planned_at: str
    execution_duration: str
    task_count: int
    completed_task_count: int
    success_task_count: int
    failed_task_count: int
    warning_task_count: int
    case_sum: int
    success: int
    fail: int
    warning: int
    success_rate: float
    api_case_sum: int = 0
    api_fail: int = 0
    ui_case_sum: int = 0
    ui_fail: int = 0
    pytest_case_sum: int = 0
    pytest_fail: int = 0
    children: list[TaskGroupChildReport] = field(default_factory=list)
    excluded_count: int = 0


class TaskGroupNoticeBuilder:
    """任务组批次使用独立通知样式，避免被误解为单个测试套报告。"""

    def __init__(self, report: TaskGroupNoticeReport, domain_name: str = '', platform_name: str = '芒果测试平台'):
        self.report = report
        self.platform_name = platform_name
        self.domain_name = domain_name.rstrip('/') if domain_name.startswith(('http://', 'https://')) else ''

    def group_report_url(self) -> str:
        if not self.domain_name:
            return ''
        if self.report.execution_id is not None:
            return (
                f'{self.domain_name}/#/report/index?'
                f'group_execution_id={self.report.execution_id}'
            )
        suite_ids = [
            str(child.test_suite_id)
            for child in self.report.children
            if child.test_suite_id is not None
        ]
        if suite_ids:
            return (
                f'{self.domain_name}/#/report/index?'
                f'test_suite_ids={",".join(suite_ids)}'
            )
        return ''

    def child_report_url(self, child: TaskGroupChildReport) -> str:
        if not self.domain_name or child.test_suite_id is None:
            return ''
        return f'{self.domain_name}/#/report/system/details?id={child.test_suite_id}'

    def build_feishu_card(self) -> dict:
        report = self.report
        failed = report.failed_task_count > 0
        warning = report.warning_task_count > 0 or report.warning > 0
        status_text = '失败' if failed else '告警' if warning else '通过'
        header_template = 'red' if failed else 'orange' if warning else 'green'
        project_product = f'{report.project_name} / {report.product_name}'
        elements = [
            {
                'tag': 'div',
                'text': {
                    'tag': 'lark_md',
                    'content': (
                        f'**项目产品：** {project_product}\n'
                        f'**测试环境：** {report.test_environment}\n'
                        f'**任务组：** {report.task_group_name}\n'
                        f'**计划时间：** {report.planned_at}'
                    ),
                },
            },
            {'tag': 'hr'},
            {
                'tag': 'column_set',
                'flex_mode': 'none',
                'background_style': 'default',
                'columns': [
                    self._metric_column('子任务', str(report.task_count), 'grey'),
                    self._metric_column('已完成', str(report.completed_task_count), 'blue'),
                    self._metric_column('成功', str(report.success_task_count), 'green'),
                    self._metric_column('失败', str(report.failed_task_count), 'red'),
                ],
            },
            {'tag': 'hr'},
            {
                'tag': 'column_set',
                'flex_mode': 'none',
                'background_style': 'default',
                'columns': [
                    self._metric_column('成功率', f'{self._format_rate(report.success_rate)}%',
                                        'green' if not failed else 'red'),
                    self._metric_column('总用例', str(report.case_sum), 'grey'),
                    self._metric_column('成功', str(report.success), 'green'),
                    self._metric_column('失败', str(report.fail), 'red'),
                ],
            },
        ]

        category_lines = self._category_lines()
        if category_lines:
            elements.extend([
                {'tag': 'hr'},
                {'tag': 'div', 'text': {'tag': 'lark_md', 'content': '\n'.join(category_lines)}},
            ])

        elements.extend([
            {'tag': 'hr'},
            {
                'tag': 'div',
                'text': {
                    'tag': 'lark_md',
                    'content': (
                        f'**告警用例：** {report.warning}\n'
                        f'**已排除用例：** {report.excluded_count}\n'
                        f'**执行耗时：** {report.execution_duration}'
                    ),
                },
            },
            {'tag': 'hr'},
            {
                'tag': 'div',
                'text': {'tag': 'lark_md', 'content': '**子任务报告**'},
            },
        ])
        child_lines = [self._feishu_child_line(child) for child in report.children]
        if child_lines:
            elements.append({
                'tag': 'div',
                'text': {
                    'tag': 'lark_md',
                    'content': '\n'.join(child_lines),
                },
            })

        group_url = self.group_report_url()
        if group_url:
            elements.append({
                'tag': 'action',
                'actions': [{
                    'tag': 'button',
                    'text': {'tag': 'plain_text', 'content': '查看全部执行报告'},
                    'type': 'primary',
                    'url': group_url,
                }],
            })
        return {
            'config': {'wide_screen_mode': True, 'enable_forward': True},
            'header': {
                'template': header_template,
                'title': {
                    'tag': 'plain_text',
                    'content': f'{self.platform_name}任务组执行报告 - {status_text}',
                },
            },
            'elements': elements,
        }

    def build_wechat_markdown(self) -> str:
        report = self.report
        failed = report.failed_task_count > 0
        status_text = '失败' if failed else '通过'
        status_color = 'warning' if failed else 'info'
        lines = [
            f'## {self.platform_name}任务组执行报告 - <font color="{status_color}">{status_text}</font>',
            f'**项目产品：** {report.project_name} / {report.product_name}',
            f'**测试环境：** {report.test_environment}',
            f'**任务组：** {report.task_group_name}',
            '>',
            f'**子任务：** {report.completed_task_count}/{report.task_count} 完成，'
            f'成功 {report.success_task_count}，失败 {report.failed_task_count}',
            f'**用例：** 总数 {report.case_sum}，成功 {report.success}，'
            f'失败 {report.fail}，告警 {report.warning}',
            f'**执行耗时：** {report.execution_duration}',
            f'**已排除用例：** {report.excluded_count}',
            '>',
            '**子任务报告**',
        ]
        lines.extend(self._wechat_child_line(child) for child in report.children)
        group_url = self.group_report_url()
        if group_url:
            lines.extend(['>', f'[查看全部执行报告]({group_url})'])
        return '\n'.join(lines)

    def build_email_html(self) -> str:
        report = self.report
        failed = report.failed_task_count > 0
        status_text = '失败' if failed else '通过'
        status_color = '#F53F3F' if failed else '#00B42A'
        rows = ''.join(self._email_child_row(child) for child in report.children)
        group_link = self.group_report_url()
        action = (
            f'<p><a href="{html.escape(group_link, quote=True)}">查看全部执行报告</a></p>'
            if group_link else ''
        )
        return f"""<!doctype html>
<html><body style="font-family:Arial,sans-serif;color:#1D2129">
<h2>{html.escape(self.platform_name)}任务组执行报告 - <span style="color:{status_color}">{status_text}</span></h2>
<p><strong>项目产品：</strong>{html.escape(report.project_name)} / {html.escape(report.product_name)}<br>
<strong>测试环境：</strong>{html.escape(report.test_environment)}<br>
<strong>任务组：</strong>{html.escape(report.task_group_name)}</p>
<p><strong>子任务：</strong>{report.completed_task_count}/{report.task_count} 完成，成功 {report.success_task_count}，失败 {report.failed_task_count}<br>
<strong>用例：</strong>总数 {report.case_sum}，成功 {report.success}，失败 {report.fail}，告警 {report.warning}<br>
<strong>已排除用例：</strong>{report.excluded_count}<br>
<strong>执行耗时：</strong>{html.escape(report.execution_duration)}</p>
<table style="border-collapse:collapse;width:100%"><thead><tr><th align="left">子任务</th><th>结果</th><th>用例</th><th>成功</th><th>失败</th><th>告警</th></tr></thead><tbody>{rows}</tbody></table>
{action}</body></html>"""

    def _feishu_child_line(self, child: TaskGroupChildReport) -> str:
        tones = {'成功': 'green', '失败': 'red', '告警': 'orange'}
        name = child.task_name
        url = self.child_report_url(child)
        if url:
            name = f'[{name}]({url})'
        return (
            f"<font color='{tones.get(child.result, 'grey')}'>{child.result}</font> "
            f'{name} · 用例 {child.case_sum} / 失败 {child.fail} / 告警 {child.warning}'
        )

    def _wechat_child_line(self, child: TaskGroupChildReport) -> str:
        name = child.task_name
        url = self.child_report_url(child)
        if url:
            name = f'[{name}]({url})'
        return f'- {child.result} {name}：用例 {child.case_sum}，失败 {child.fail}，告警 {child.warning}'

    def _email_child_row(self, child: TaskGroupChildReport) -> str:
        name = html.escape(child.task_name)
        url = self.child_report_url(child)
        if url:
            name = f'<a href="{html.escape(url, quote=True)}">{name}</a>'
        cells = [name, html.escape(child.result), child.case_sum, child.success, child.fail, child.warning]
        return '<tr>' + ''.join(
            f'<td style="padding:8px;border-top:1px solid #E5E6EB">{value}</td>' for value in cells) + '</tr>'

    def _category_lines(self) -> list[str]:
        report = self.report
        result = []
        for name, case_sum, fail_sum in [
            ('接口', report.api_case_sum, report.api_fail),
            ('UI', report.ui_case_sum, report.ui_fail),
            ('单元', report.pytest_case_sum, report.pytest_fail),
        ]:
            if case_sum:
                result.append(f'**{name}用例：** {case_sum} 个，失败 {fail_sum} 个')
        return result

    @staticmethod
    def _metric_column(label: str, value: str, color: str) -> dict:
        return {
            'tag': 'column',
            'width': 'weighted',
            'weight': 1,
            'elements': [{
                'tag': 'div',
                'text': {
                    'tag': 'lark_md',
                    'content': f"**{label}**\n<font color='{color}'>{value}</font>",
                },
            }],
        }

    @staticmethod
    def _format_rate(value: float) -> str:
        return f'{float(value):.2f}'.rstrip('0').rstrip('.')
