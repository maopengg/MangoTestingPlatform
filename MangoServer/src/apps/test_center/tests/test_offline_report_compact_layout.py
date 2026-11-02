from html.parser import HTMLParser

from django.test import SimpleTestCase

from src.apps.test_center.services.offline_report.renderer import ReportHtmlService
from src.apps.test_center.tests.test_report_delivery import sample_snapshot


class ScopeHelpParser(HTMLParser):
    def __init__(self, content):
        super().__init__()
        self.help = []
        self.feed(content)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'details' and attrs.get('class') == 'mango-report-help':
            self.help.append(attrs)


class OfflineReportCompactLayoutTests(SimpleTestCase):
    def test_successful_group_children_have_no_repeated_empty_detail_blocks(self):
        snapshot = sample_snapshot()
        snapshot.update(source_kind='group', failed_cases_only=True)
        snapshot['suites'] = [{'name': f'子任务 {index}', 'result': '通过', 'cases': [],
                               'summary': {'case_sum': 13, 'success': 13, 'fail': 0}} for index in range(21)]
        content = ReportHtmlService.render(snapshot, '示例平台').decode()
        self.assertEqual(content.count('<section id="suite-'), 21)
        self.assertEqual(content.count('<p class="mango-child-counts">'), 21)
        self.assertNotIn('<p class="mango-empty">', content)
        self.assertNotIn('当前子任务没有可展示', content)
        self.assertEqual(content.count('仅展示失败明细'), 1)

    def test_failed_child_without_details_keeps_a_short_neutral_hint(self):
        snapshot = sample_snapshot()
        snapshot.update(source_kind='group', failed_cases_only=True)
        snapshot['suites'] = [{'name': '失败子任务', 'result': '失败', 'cases': [], 'summary': {'fail': 1}}]
        content = ReportHtmlService.render(snapshot, '示例平台').decode()
        self.assertIn('<p class="mango-empty">暂无失败明细</p>', content)
        self.assertNotIn('明细已按保留策略清理', content)

    def test_scope_is_one_short_strip_with_collapsed_explanation_and_named_link(self):
        snapshot = sample_snapshot()
        url = 'https://reports.example.com/#/report/system/details?id=1'
        snapshot.update(failed_cases_only=True, online_url=url)
        content = ReportHtmlService.render(snapshot, '示例平台').decode()
        self.assertEqual(content.count('<aside class="mango-report-scope"'), 1)
        self.assertNotIn('<aside class="mango-report-notice"', content)
        self.assertIn('仅展示失败明细', content)
        self.assertIn('>完整报告（需要内网访问）</a>', content)
        self.assertEqual(content.count(url), 1)
        help_blocks = ScopeHelpParser(content).help
        self.assertEqual(len(help_blocks), 1)
        self.assertNotIn('open', help_blocks[0])
        self.assertIn('汇总统计仍包含全部用例', content)

    def test_single_report_does_not_repeat_task_name_and_summary_in_case_heading(self):
        snapshot = sample_snapshot()
        snapshot['suites'][0].update(name=snapshot['name'], summary=snapshot['summary'])
        content = ReportHtmlService.render(snapshot, '示例平台').decode()
        self.assertIn('<h2>用例明细</h2>', content)
        self.assertNotIn(f'<h2>{snapshot["name"]}</h2>', content)
        self.assertNotIn('<p class="mango-child-counts">', content)

    def test_group_keeps_child_names_and_statistics(self):
        snapshot = sample_snapshot()
        snapshot['source_kind'] = 'group'
        snapshot['suites'][0].update(name='示例子任务', summary=snapshot['summary'])
        content = ReportHtmlService.render(snapshot, '示例平台').decode()
        self.assertIn('<h2>示例子任务</h2>', content)
        self.assertIn('<p class="mango-child-counts">', content)

    def test_no_failure_filter_keeps_full_report_link_without_failure_notice(self):
        for source in ('suite', 'group'):
            snapshot = sample_snapshot()
            snapshot.update(source_kind=source, failed_cases_only=False, online_url='https://reports.example.com/report?id=1')
            content = ReportHtmlService.render(snapshot, '示例平台').decode()
            self.assertEqual(ScopeHelpParser(content).help, [])
            self.assertIn('href="https://reports.example.com/report?id=1"', content)
            self.assertIn('完整报告（需要内网访问）', content)
            self.assertNotIn('仅展示失败明细', content)

    def test_missing_or_unsafe_platform_url_is_not_a_clickable_link(self):
        for url in ('', 'javascript:alert(1)'):
            snapshot = sample_snapshot()
            snapshot.update(failed_cases_only=False, online_url=url)
            content = ReportHtmlService.render(snapshot, '示例平台').decode()
            self.assertIn('完整报告（需要内网访问，未配置平台地址）', content)
            self.assertNotIn('href="javascript:', content)
