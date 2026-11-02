import base64
import hashlib
import re
from html.parser import HTMLParser
from pathlib import Path

from django.test import SimpleTestCase

from src.apps.test_center.services.offline_report.renderer import ReportHtmlService
from src.apps.test_center.tests.test_offline_api_details import api_example
from src.apps.test_center.tests.test_report_delivery import sample_snapshot


class CaseViewParser(HTMLParser):
    def __init__(self, content):
        super().__init__()
        self.ids, self.links = [], []
        self.script_sources, self.handlers = [], []
        self.feed(content)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        if 'data-case-open' in attrs:
            self.links.append(attrs['href'][1:])
        if tag == 'script' and 'src' in attrs:
            self.script_sources.append(attrs['src'])
        self.handlers.extend(key for key in attrs if key.startswith('on'))


class OfflineCaseViewTests(SimpleTestCase):
    def test_case_links_match_unique_templates_even_when_case_ids_repeat(self):
        snapshot = sample_snapshot()
        snapshot['suites'][0]['cases'][0]['payload'] = [api_example(), api_example()]
        snapshot['suites'] *= 2
        content = ReportHtmlService.render(snapshot, '示例平台').decode()
        parser = CaseViewParser(content)
        self.assertEqual(parser.links, ['case-1-1', 'case-2-1'])
        self.assertTrue(set(parser.links) <= set(parser.ids))
        self.assertEqual(len(parser.ids), len(set(parser.ids)))
        self.assertIn('<dialog id="mango-case-dialog"', content)
        self.assertIn('aria-labelledby="mango-case-title"', content)
        self.assertIn('data-case-close>返回报告', content)

    def test_csp_allows_only_exact_trusted_embedded_script_and_no_data_handlers(self):
        snapshot = sample_snapshot()
        snapshot['suites'][0]['cases'][0]['name'] = '</template><script>dangerous()</script>'
        content = ReportHtmlService.render(snapshot, '示例平台').decode()
        scripts = re.findall(r'<script>(.*?)</script>', content, re.S)
        self.assertEqual(len(scripts), 1)
        asset = Path(__file__).parents[1] / 'services/offline_report/assets/report.js'
        self.assertEqual(scripts[0], asset.read_text())
        digest = base64.b64encode(hashlib.sha256(scripts[0].encode()).digest()).decode()
        self.assertIn(f"script-src 'sha256-{digest}'", content)
        self.assertNotIn("script-src 'unsafe-inline'", content)
        self.assertNotIn('<script>dangerous()', content)
        parser = CaseViewParser(content)
        self.assertEqual(parser.handlers, [])
        self.assertEqual(parser.script_sources, [])
        self.assertNotRegex(scripts[0], r'\b(?:fetch|eval|XMLHttpRequest|innerHTML|document\.write)\b')

    def test_mobile_detail_view_and_return_navigation_are_embedded(self):
        content = ReportHtmlService.render(sample_snapshot(), '示例平台').decode()
        for expected in ('history.back()', "window.addEventListener('hashchange'", 'dialog.showModal()',
                         "dialog.addEventListener('cancel'", "event.key === 'ArrowRight'", 'content.cloneNode(true)',
                         '.mango-case-dialog{width:100vw;min-width:0}', 'height:100dvh'):
            self.assertIn(expected, content)
