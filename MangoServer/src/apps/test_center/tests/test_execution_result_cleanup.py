from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings
from django.utils import timezone

from src.apps.test_center.services.results.execution_result import ExecutionResultService
from src.common.storage import MangoMinioMediaStorage


@override_settings(FILE_STORAGE_ROOT='platform/test', RESULT_DATA_FILE_PREFIX='result')
class ExecutionResultCleanupTests(SimpleTestCase):
    def test_failed_delete_preserves_payload_for_next_cleanup(self):
        row = SimpleNamespace(id=1, result_object_key='result/old.json', result_data={'status': 0}, save=Mock())
        queryset = Mock()
        queryset.distinct.return_value.iterator.return_value = iter([row])
        with patch('src.apps.test_center.services.results.execution_result.ExecutionResult.objects.filter', return_value=queryset), \
                patch('src.apps.test_center.services.results.execution_result.default_storage.delete', side_effect=OSError('unavailable')), \
                patch('src.apps.test_center.services.results.execution_result.log'):
            self.assertEqual(ExecutionResultService.clear_expired_result_data(60), 0)
        row.save.assert_not_called()
        self.assertEqual(row.result_data, {'status': 0})

    def test_successful_delete_marks_record_cleaned(self):
        row = SimpleNamespace(id=1, result_object_key='result/old.json', result_data={'status': 0}, save=Mock())
        queryset = Mock()
        queryset.distinct.return_value.iterator.return_value = iter([row])
        with patch('src.apps.test_center.services.results.execution_result.ExecutionResult.objects.filter', return_value=queryset), \
                patch('src.apps.test_center.services.results.execution_result.default_storage.delete') as delete:
            self.assertEqual(ExecutionResultService.clear_expired_result_data(60), 1)
        delete.assert_called_once_with('result/old.json')
        self.assertTrue(row.result_cleaned)
        self.assertIsNone(row.result_data)

    def test_sweep_only_deletes_old_generated_results_in_current_environment(self):
        now = timezone.now()
        old = now - timedelta(days=100)
        date = old.strftime('%Y/%m/%d')
        uuid = 'a' * 32
        eligible = f'platform/test/result/{date}/report_1/detail_2/{uuid}.json'
        files = [
            (eligible, old),
            (f'platform/master/result/{date}/api_case_1/{uuid}.json', old),
            (f'platform/test/result/{date}/api_case_1/{uuid}.json', now),
            (f'platform/test/result/{now:%Y/%m/%d}/api_case_1/{uuid}.json', old),
            (f'platform/test/result/{date}/uploaded.json', old),
            (f'platform/test/result/{date}/api_case_1/{uuid}.txt', old),
        ]
        with patch('src.apps.test_center.services.results.execution_result.iter_current_storage_files', return_value=iter(files)), \
                patch('src.apps.test_center.services.results.execution_result.delete_current_storage_file') as delete:
            result = ExecutionResultService.cleanup_expired_storage_files(60)
        delete.assert_called_once_with(eligible)
        self.assertEqual(result['deleted_file_count'], 1)

    def test_sweep_failure_is_visible_and_file_is_retried(self):
        old = timezone.now() - timedelta(days=100)
        name = f'result/{old:%Y/%m/%d}/ui_case_1/{"b" * 32}.json'
        with patch('src.apps.test_center.services.results.execution_result.iter_current_storage_files', side_effect=lambda _: iter([(name, old)])), \
                patch('src.apps.test_center.services.results.execution_result.delete_current_storage_file', side_effect=[OSError('unavailable'), None]) as delete, \
                patch('src.apps.test_center.services.results.execution_result.log'):
            first = ExecutionResultService.cleanup_expired_storage_files(60)
            second = ExecutionResultService.cleanup_expired_storage_files(60)
        self.assertEqual(first['failed_file_count'], 1)
        self.assertEqual(second['deleted_file_count'], 1)
        self.assertEqual(delete.call_count, 2)

    def test_scan_failure_is_reported(self):
        with patch('src.apps.test_center.services.results.execution_result.iter_current_storage_files', side_effect=OSError('unavailable')), \
                patch('src.apps.test_center.services.results.execution_result.log'):
            result = ExecutionResultService.cleanup_expired_storage_files(60)
        self.assertTrue(result['storage_scan_failed'])

    def test_object_listing_is_scoped_to_exact_environment_prefix(self):
        storage = object.__new__(MangoMinioMediaStorage)
        storage.location = 'platform/test'
        storage.legacy_locations = []
        storage.bucket_name = 'results'
        storage.client = Mock()
        storage.client.list_objects.return_value = []
        self.assertEqual(list(storage.iter_current_files('result')), [])
        storage.client.list_objects.assert_called_once_with('results', prefix='platform/test/result/', recursive=True)
