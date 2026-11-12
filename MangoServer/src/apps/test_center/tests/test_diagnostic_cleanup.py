from contextlib import nullcontext
from datetime import timedelta
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings
from django.utils import timezone

from src.apps.test_center.services.diagnostics.diagnostic_markdown import DiagnosticMarkdownService


@override_settings(FILE_STORAGE_ROOT='platform/test')
class DiagnosticCleanupTests(SimpleTestCase):
    def test_expired_documents_are_deleted_and_only_matching_bindings_are_cleared(self):
        old = timezone.now() - timedelta(days=100)
        stamp = old.strftime('%Y%m%d%H%M%S%f')
        scheduled = f'platform/test/diagnostics/scheduled-tasks/12/{stamp}-result.md'
        report = f'platform/test/diagnostics/test-reports/34/{stamp}-result.md'
        task_model, report_model = Mock(), Mock()
        with patch.object(DiagnosticMarkdownService, '_MODEL_MAP', {
            'scheduled_task': (task_model, 'scheduled-tasks'),
            'test_report': (report_model, 'test-reports'),
        }), patch('src.apps.test_center.services.diagnostics.diagnostic_markdown.transaction.atomic', side_effect=nullcontext), \
                patch('src.apps.test_center.services.diagnostics.diagnostic_markdown.iter_current_storage_files', return_value=iter([(scheduled, old), (report, old)])), \
                patch('src.apps.test_center.services.diagnostics.diagnostic_markdown.delete_current_storage_file') as delete:
            result = DiagnosticMarkdownService.cleanup_expired(60)
        self.assertEqual(result['diagnostic_deleted_file_count'], 2)
        self.assertEqual(delete.call_count, 2)
        task_model.objects.filter.assert_called_once_with(
            id=12, diagnostic_file_path__in=[scheduled, scheduled[len('platform/test/'):]],
        )
        task_model.objects.filter.return_value.update.assert_called_once_with(diagnostic_file_path=None)
        report_model.objects.filter.return_value.update.assert_called_once_with(diagnostic_file_path=None)

    def test_new_files_other_environments_and_unknown_names_are_preserved(self):
        now = timezone.now()
        old = now - timedelta(days=100)
        files = [
            (f'platform/test/diagnostics/test-reports/1/{now:%Y%m%d%H%M%S%f}-result.md', old),
            (f'platform/master/diagnostics/test-reports/1/{old:%Y%m%d%H%M%S%f}-result.md', old),
            ('platform/test/diagnostics/other.md', old),
            (f'platform/test/diagnostics/test-reports/1/{old:%Y%m%d%H%M%S%f}-result.md', now),
        ]
        with patch('src.apps.test_center.services.diagnostics.diagnostic_markdown.iter_current_storage_files', return_value=iter(files)), \
                patch('src.apps.test_center.services.diagnostics.diagnostic_markdown.delete_current_storage_file') as delete:
            result = DiagnosticMarkdownService.cleanup_expired(60)
        delete.assert_not_called()
        self.assertEqual(result['diagnostic_deleted_file_count'], 0)

    def test_database_failure_does_not_delete_file(self):
        old = timezone.now() - timedelta(days=100)
        name = f'diagnostics/test-reports/1/{old:%Y%m%d%H%M%S%f}-result.md'
        model = Mock()
        model.objects.filter.return_value.update.side_effect = OSError('database unavailable')
        with patch.object(DiagnosticMarkdownService, '_MODEL_MAP', {'test_report': (model, 'test-reports')}), \
                patch('src.apps.test_center.services.diagnostics.diagnostic_markdown.transaction.atomic', side_effect=nullcontext), \
                patch('src.apps.test_center.services.diagnostics.diagnostic_markdown.iter_current_storage_files', return_value=iter([(name, old)])), \
                patch('src.apps.test_center.services.diagnostics.diagnostic_markdown.delete_current_storage_file') as delete, \
                patch('src.apps.test_center.services.diagnostics.diagnostic_markdown.log'):
            result = DiagnosticMarkdownService.cleanup_expired(60)
        delete.assert_not_called()
        self.assertEqual(result['diagnostic_failed_file_count'], 1)
