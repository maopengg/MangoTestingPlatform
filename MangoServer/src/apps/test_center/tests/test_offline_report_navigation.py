from html.parser import HTMLParser

from django.test import SimpleTestCase

from src.apps.test_center.enums.report_delivery import ReportSourceEnum
from src.apps.test_center.services.offline_report.renderer import ReportHtmlService
from src.apps.test_center.tests.test_report_delivery import sample_snapshot


class NavigationParser(HTMLParser):
    def __init__(self, content):
        super().__init__()
        self.links = []
        self.sections = []
        self.mobile = []
        self.feed(content)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a' and attrs.get('href', '').startswith('#suite-'):
            self.links.append(attrs['href'])
        if tag == 'section' and attrs.get('id', '').startswith('suite-'):
            self.sections.append(attrs['id'])
        if tag == 'details' and attrs.get('class') == 'mango-report-toc-mobile':
            self.mobile.append(attrs)


class OfflineReportNavigationTests(SimpleTestCase):
    def test_group_directory_includes_all_tasks_and_every_anchor_exists(self):
        snapshot = sample_snapshot()
        snapshot['source_kind'] = ReportSourceEnum.GROUP.value
        snapshot['suites'] = [{'name': f'子任务 {index}', 'result': '通过', 'cases': []} for index in range(40)]
        content = ReportHtmlService.render(snapshot, '示例平台').decode()
        parsed = NavigationParser(content)
        expected = [f'#suite-{index}' for index in range(1, 41)]
        self.assertEqual(parsed.links, expected + expected)
        self.assertEqual(parsed.sections, [link[1:] for link in expected])
        self.assertIn('子任务目录（40）', content)
        self.assertIn('position:sticky', content)
        self.assertIn('overflow-y:auto', content)

    def test_mobile_directory_is_collapsed_by_default(self):
        snapshot = sample_snapshot()
        snapshot['source_kind'] = ReportSourceEnum.GROUP.value
        content = ReportHtmlService.render(snapshot, '示例平台').decode()
        parsed = NavigationParser(content)
        self.assertEqual(len(parsed.mobile), 1)
        self.assertNotIn('open', parsed.mobile[0])
        self.assertEqual(content.count('<script>'), 1)
        self.assertIn('@media(max-width:900px)', content)

    def test_single_execution_report_has_no_directory(self):
        snapshot = sample_snapshot()
        snapshot['source_kind'] = ReportSourceEnum.SUITE.value
        content = ReportHtmlService.render(snapshot, '示例平台').decode()
        self.assertEqual(NavigationParser(content).links, [])
        self.assertEqual(NavigationParser(content).mobile, [])
        self.assertNotIn('<aside class="mango-report-toc">', content)

    def test_group_with_one_child_still_has_directory_and_escapes_its_name(self):
        snapshot = sample_snapshot()
        snapshot['source_kind'] = ReportSourceEnum.GROUP.value
        snapshot['suites'][0]['name'] = '<img src=x onerror=alert(1)>"子任务'
        content = ReportHtmlService.render(snapshot, '示例平台').decode()
        self.assertIn('子任务目录（1）', content)
        self.assertIn('&lt;img src=x', content)
        self.assertNotIn('<img src=x', content)
        self.assertEqual(NavigationParser(content).links, ['#suite-1', '#suite-1'])
