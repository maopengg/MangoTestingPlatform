import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest import TestCase

from src.services.pytest.test_case import TestCase as Runner
from tests.test_pytest_execution_lifecycle import build_case_model


class PytestCompletionTests(TestCase):
    def run_pytest(self, source, *options, extra_source=None):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'test_example.py').write_text(source, encoding='utf-8')
            if extra_source is not None:
                (root / 'test_broken.py').write_text(extra_source, encoding='utf-8')
            metadata = root / 'completion.json'
            env = {**os.environ, 'MANGO_PYTEST_COMPLETION_FILE': str(metadata),
                   'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1',
                   'PYTHONPATH': str(Path(__file__).resolve().parents[1] / 'src/services/pytest')}
            completed = subprocess.run(
                [sys.executable, '-m', 'pytest', '-q', '-p', 'result_tracking',
                 '--confcutdir', str(root), str(root), *options],
                cwd=root, env=env, capture_output=True, text=True, timeout=20,
            )
            self.assertTrue(metadata.exists(), completed.stderr)
            return completed.returncode, json.loads(metadata.read_text(encoding='utf-8'))

    def test_parametrized_tests_are_collected_as_individual_items(self):
        code, data = self.run_pytest('import pytest\n@pytest.mark.parametrize("n", [1,2,3])\ndef test_value(n):\n assert n > 0\n')
        self.assertEqual(code, 0)
        self.assertEqual(data, {'collected_count': 3, 'results_complete': True})

    def test_failure_and_skip_still_produce_complete_result_set(self):
        code, data = self.run_pytest('import pytest\ndef test_failed():\n assert False\n@pytest.mark.skip\ndef test_skipped():\n pass\n')
        self.assertEqual(code, 1)
        self.assertEqual(data, {'collected_count': 2, 'results_complete': True})

    def test_fail_fast_does_not_claim_remaining_tests_were_executed(self):
        code, data = self.run_pytest('def test_first():\n assert False\ndef test_second():\n pass\n', '-x')
        self.assertEqual(code, 1)
        self.assertEqual(data, {'collected_count': 2, 'results_complete': False})

    def test_collection_error_and_no_tests_never_claim_completeness(self):
        for source in ('raise RuntimeError("collection failed")\n', 'value = 1\n'):
            with self.subTest(source=source):
                code, data = self.run_pytest(source)
                self.assertNotIn(code, (0, 1))
                self.assertFalse(data['results_complete'])

    def test_continue_after_collection_error_still_does_not_claim_completeness(self):
        code, data = self.run_pytest('def test_good():\n pass\n', '--continue-on-collection-errors',
                                     extra_source='raise RuntimeError("collection failed")\n')
        self.assertEqual(code, 1)
        self.assertEqual(data['collected_count'], 1)
        self.assertFalse(data['results_complete'])

    def test_parent_requires_matching_allure_items_and_successful_process_completion(self):
        with TemporaryDirectory() as directory:
            metadata = Path(directory) / 'completion.json'
            metadata.write_text(json.dumps({'collected_count': 3, 'results_complete': True}), encoding='utf-8')
            for code, items, message, expected in (
                (0, [{'status': 'passed'}] * 3, None, True),
                (1, [{'status': 'failed'}] * 3, None, True),
                (0, [{'status': 'passed'}], None, False),
                (2, [{'status': 'passed'}] * 3, None, False),
                (0, [{'status': 'passed'}] * 3, 'startup failed', False),
            ):
                with self.subTest(code=code, length=len(items), message=message):
                    runner = Runner(None, build_case_model(), report_result=False)
                    runner.pytest_error_message = message
                    runner.read_completion(metadata, items, code)
                    self.assertEqual(runner.case_result.results_complete, expected)
            for content in ('invalid', '[]', '{"collected_count": true}', '{}'):
                metadata.write_text(content, encoding='utf-8')
                runner = Runner(None, build_case_model(), report_result=False)
                runner.read_completion(metadata, [], 0)
                self.assertFalse(runner.case_result.results_complete)
