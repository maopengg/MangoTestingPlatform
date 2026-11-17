"""Run with either component's Python; no database or running services required."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

import pymupdf
from mangotools.decorator import func_info

ROOT = Path(__file__).resolve().parents[1]
METHODS = ('assert_pdf_comparison_pass', 'assert_pdf_visual_match', 'assert_pdf_text_match',
           'assert_pdf_layout_match', 'assert_pdf_color_match')


def adapter(relative_path):
    spec = importlib.util.spec_from_file_location('component_assertion', ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.ObtainAssertion()


class FileVisualIntegrationTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.adapters = [adapter('MangoServer/src/common/testing/assertion.py'),
                         adapter('MangoActuator/src/customization/assertion.py')]

    def pdf(self, name, color=None, blank=False):
        path = self.root / (name + '.pdf')
        with pymupdf.open() as doc:
            page = doc.new_page(width=120, height=120)
            page.insert_text((10, 30), 'Order sample')
            if color is not None:
                page.draw_rect(pymupdf.Rect(20, 60, 60, 90), color=color, fill=color)
            if blank:
                doc.new_page(width=120, height=120)
            doc.save(path)
        return str(path)

    def test_top_level_registration_and_inline_parameters(self):
        category = next(item for item in func_info if item['value'] == '文件视觉识别')
        methods = {item['value']: item for group in category['children'] for item in group['children']}
        self.assertEqual(set(METHODS), set(methods))
        for method in methods.values():
            self.assertEqual([p['f'] for p in method['parameter']], ['actual', 'expect'])
            self.assertTrue(all(p['input_type'] == 'object' for p in method['parameter']))

    def test_both_components_preserve_legal_blank_page(self):
        path = self.pdf('blank', blank=True)
        for component in self.adapters:
            for method in METHODS:
                with self.subTest(component=type(component), method=method):
                    self.assertIn('通过', component.ass(method, {'文件路径': path}, {'基准文件路径': path}))

    def test_both_components_reject_deleted_blank_page(self):
        baseline = self.pdf('baseline', blank=True)
        actual = self.pdf('actual')
        for component in self.adapters:
            for method in METHODS:
                with self.subTest(method=method), self.assertRaisesRegex(AssertionError, '页数不一致'):
                    component.ass(method, actual, {'基准文件路径': baseline})

    def test_color_difference_passes_gray_but_fails_rgb_and_combined(self):
        baseline = self.pdf('red', (1, 0, 0))
        actual = self.pdf('blue', (0, 0, 1))
        for component in self.adapters:
            self.assertIn('通过', component.ass('assert_pdf_visual_match', actual, {'基准文件路径': baseline}))
            for method in ('assert_pdf_color_match', 'assert_pdf_comparison_pass'):
                with self.subTest(method=method), self.assertRaisesRegex(AssertionError, '颜色差异'):
                    component.ass(method, actual, {'基准文件路径': baseline})


if __name__ == '__main__':
    unittest.main(verbosity=2)
