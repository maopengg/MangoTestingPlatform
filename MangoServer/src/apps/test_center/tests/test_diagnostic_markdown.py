from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from django.utils import timezone

from src.apps.test_center.exceptions import TestCenterError
from src.apps.test_center.services.diagnostic_markdown import DiagnosticMarkdownService


class DiagnosticMarkdownServiceTests(SimpleTestCase):
    def test_rejects_non_markdown_file_names(self):
        for file_name in ('diagnostic.txt', 'diagnostic.md.exe', 'diagnostic'):
            with self.subTest(file_name=file_name):
                with self.assertRaisesRegex(TestCenterError, '必须以 \\.md 结尾'):
                    DiagnosticMarkdownService._safe_file_name(file_name)

    def test_accepts_markdown_file_name_case_insensitively(self):
        self.assertEqual(
            DiagnosticMarkdownService._safe_file_name('诊断报告.MD'),
            '诊断报告.md',
        )

    def test_diagnostic_files_use_independent_object_storage_directories(self):
        cases = (
            (
                DiagnosticMarkdownService.TARGET_SCHEDULED_TASK,
                'diagnostics/scheduled-tasks/12/20260824123000123456-result.md',
            ),
            (
                DiagnosticMarkdownService.TARGET_TEST_REPORT,
                'diagnostics/test-reports/34/20260824123000123456-result.md',
            ),
        )

        for target_type, expected in cases:
            _, directory = DiagnosticMarkdownService._target_config(target_type)
            target_id = 12 if target_type == DiagnosticMarkdownService.TARGET_SCHEDULED_TASK else 34
            storage_name = DiagnosticMarkdownService._build_storage_name(
                directory,
                target_id,
                '20260824123000123456',
                'result.md',
            )

            self.assertEqual(storage_name, expected)
            self.assertFalse(storage_name.startswith(('test_file/', 'uitest/')))

    @patch(
        'src.apps.test_center.services.diagnostic_markdown.build_public_file_url',
        return_value='https://files.example.com/diagnostic.md',
    )
    @patch('src.apps.test_center.services.diagnostic_markdown.default_storage.get_modified_time')
    def test_metadata_returns_download_url(self, get_modified_time, build_url):
        modified_time = timezone.now()
        get_modified_time.return_value = modified_time
        target = SimpleNamespace(
            id=12,
            diagnostic_file_path=(
                'diagnostics/scheduled-tasks/12/'
                '20260824123000123456-api-regression.md'
            ),
            update_time=modified_time,
        )

        result = DiagnosticMarkdownService.metadata(
            DiagnosticMarkdownService.TARGET_SCHEDULED_TASK,
            target,
        )

        self.assertEqual(result['file_name'], 'api-regression.md')
        self.assertEqual(
            result['download_url'],
            'https://files.example.com/diagnostic.md',
        )
        build_url.assert_called_once_with(target.diagnostic_file_path)
