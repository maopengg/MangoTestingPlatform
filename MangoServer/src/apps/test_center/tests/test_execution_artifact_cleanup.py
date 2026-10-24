from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from django.utils import timezone
from mangotools.enums import CacheValueTypeEnum

from src.apps.system.models import CacheData
from src.apps.system.services.system_config import SystemConfigService, get_config_definition_map
from src.apps.test_center.services.execution_artifact import ExecutionArtifactService


class ExecutionArtifactConfigurationTests(SimpleTestCase):
    def test_missing_retention_config_uses_registered_thirty_day_default(self):
        definition = get_config_definition_map()['UI_ARTIFACT_RETENTION_DAYS']
        self.assertEqual(definition.default_value, 30)
        with patch.dict(SystemConfigService._runtime_int_cache, {}, clear=True), \
                patch('src.apps.system.services.system_config.CacheData.objects.get', side_effect=CacheData.DoesNotExist) as get:
            self.assertEqual(SystemConfigService.get_ranged_int('UI_ARTIFACT_RETENTION_DAYS'), 30)
        get.assert_called_once_with(key='UI_ARTIFACT_RETENTION_DAYS')

    def test_retention_uses_database_value(self):
        stored = SimpleNamespace(value='60', value_type=CacheValueTypeEnum.INT.value)
        with patch.dict(SystemConfigService._runtime_int_cache, {}, clear=True), \
                patch('src.apps.system.services.system_config.CacheData.objects.get', return_value=stored):
            self.assertEqual(SystemConfigService.get_ranged_int('UI_ARTIFACT_RETENTION_DAYS'), 60)

    def test_missing_or_empty_storage_directory_keeps_default_paths(self):
        for value in (None, ''):
            with self.subTest(value=value), override_settings(UI_EXECUTION_ARTIFACT_ROOT_DIR=value):
                self.assertEqual(ExecutionArtifactService.screenshot_dir(), 'uitest/screenshot')
                self.assertEqual(ExecutionArtifactService.videos_dir(), 'uitest/videos')

    @override_settings(UI_EXECUTION_ARTIFACT_ROOT_DIR='custom-ui')
    def test_deployment_storage_directory_override_is_preserved(self):
        self.assertEqual(ExecutionArtifactService.screenshot_dir(), 'custom-ui/screenshot')
        self.assertEqual(ExecutionArtifactService.videos_dir(), 'custom-ui/videos')


@override_settings(FILE_STORAGE_ROOT='platform/test', UI_EXECUTION_ARTIFACT_ROOT_DIR='uitest')
class ExecutionArtifactCleanupTests(SimpleTestCase):
    @patch('src.apps.system.services.system_config.SystemConfigService.get_ranged_int', return_value=30)
    def test_agent_evidence_including_zip_and_json_is_cleaned(self, _config):
        old = timezone.now() - timedelta(days=100)
        prefix = f'platform/test/uitest/agent-executions/{old:%Y/%m/%d}/{"a" * 32}/'
        names = [prefix + 'b' * 32 + '-trace.zip', prefix + 'c' * 32 + '-result.json']
        def files(directory):
            return iter((name, old) for name in names) if directory == 'uitest/agent-executions' else iter([])
        with patch('src.apps.test_center.services.execution_artifact.iter_current_storage_files', side_effect=files), \
                patch('src.apps.test_center.services.execution_artifact.delete_current_storage_file') as delete:
            result = ExecutionArtifactService.cleanup_expired()
        self.assertEqual(result['ui_artifact_deleted_file_count'], 2)
        self.assertEqual(delete.call_count, 2)

    def test_perf_capture_cleanup_uses_result_retention_and_preserves_unknown_files(self):
        old = timezone.now() - timedelta(days=100)
        recent = timezone.now() - timedelta(days=40)
        files = [
            ('platform/test/perf/capture/perf-run-1-node-2.csv', old),
            ('platform/test/perf/capture/perf-run-2-node-3.csv', recent),
            ('platform/test/perf/capture/customer.csv', old),
            ('platform/master/perf/capture/perf-run-4-node-5.csv', old),
        ]
        with patch('src.apps.test_center.services.execution_artifact.iter_current_storage_files', return_value=iter(files)), \
                patch('src.apps.test_center.services.execution_artifact.delete_current_storage_file') as delete:
            result = ExecutionArtifactService.cleanup_perf_captures(60)
        delete.assert_called_once_with(files[0][0])
        self.assertEqual(result['perf_capture_deleted_file_count'], 1)

    @patch('src.apps.system.services.system_config.SystemConfigService.get_ranged_int', return_value=30)
    def test_all_old_months_and_legacy_directories_are_cleaned(self, config):
        old = timezone.now() - timedelta(days=100)
        names = {
            'uitest/screenshot': ['failure.png', '2026/07/old.jpg', '2026/08/old.webp'],
            'uitest/videos': ['2026/07/old.webm'],
            'uitest/video': ['old.mp4'],
            'screenshot': ['old.png'],
            'video': ['old.webm'],
        }
        def files(directory):
            return iter((f'platform/test/{directory}/{name}', old) for name in names.get(directory, []))
        with patch('src.apps.test_center.services.execution_artifact.iter_current_storage_files', side_effect=files), \
                patch('src.apps.test_center.services.execution_artifact.delete_current_storage_file') as delete:
            result = ExecutionArtifactService.cleanup_expired()
        self.assertEqual(result['ui_artifact_deleted_file_count'], 7)
        self.assertEqual(delete.call_count, 7)
        config.assert_called_once_with('UI_ARTIFACT_RETENTION_DAYS')

    @patch('src.apps.system.services.system_config.SystemConfigService.get_ranged_int', return_value=60)
    def test_retention_recent_files_other_environments_and_unrelated_files_are_preserved(self, _config):
        now = timezone.now()
        files = [
            ('platform/test/uitest/screenshot/recent.png', now - timedelta(days=40)),
            ('platform/master/uitest/screenshot/old.png', now - timedelta(days=100)),
            ('platform/test/uitest/screenshot/readme.md', now - timedelta(days=100)),
        ]
        with patch('src.apps.test_center.services.execution_artifact.iter_current_storage_files', side_effect=lambda _: iter(files)), \
                patch('src.apps.test_center.services.execution_artifact.delete_current_storage_file') as delete:
            result = ExecutionArtifactService.cleanup_expired()
        delete.assert_not_called()
        self.assertEqual(result['ui_artifact_retention_days'], 60)

    @patch('src.apps.system.services.system_config.SystemConfigService.get_ranged_int', return_value=30)
    def test_failed_file_is_retried_on_next_run(self, _config):
        old = timezone.now() - timedelta(days=100)
        def files(directory):
            return iter([('platform/test/uitest/screenshot/old.png', old)] if directory == 'uitest/screenshot' else [])
        with patch('src.apps.test_center.services.execution_artifact.iter_current_storage_files', side_effect=files), \
                patch('src.apps.test_center.services.execution_artifact.delete_current_storage_file', side_effect=[OSError('unavailable'), None]), \
                patch('src.apps.test_center.services.execution_artifact.log'):
            first = ExecutionArtifactService.cleanup_expired()
            second = ExecutionArtifactService.cleanup_expired()
        self.assertEqual(first['ui_artifact_failed_file_count'], 1)
        self.assertEqual(second['ui_artifact_deleted_file_count'], 1)
