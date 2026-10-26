import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from src.interfaces.mcp.tools.api.helper_parts import case_result


class ApiCaseResultExportTests(SimpleTestCase):
    now = 1_800_000_000.0
    retention_seconds = 7 * 24 * 60 * 60

    def create_file(self, path, modified_at):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{}', encoding='utf-8')
        os.utime(path, (modified_at, modified_at))
        return path

    def test_export_cleans_only_expired_files_with_or_without_timezone_support(self):
        for use_tz in (False, True):
            with self.subTest(use_tz=use_tz), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                export_dir = root / case_result.API_CASE_RESULT_EXPORT_RELATIVE_DIR
                cutoff = self.now - self.retention_seconds
                expired = self.create_file(export_dir / 'expired.json', cutoff - 1)
                boundary = self.create_file(export_dir / 'boundary.json', cutoff)
                recent = self.create_file(export_dir / 'recent.json', cutoff + 1)
                unrelated = self.create_file(root / 'other' / 'expired.json', cutoff - 1)
                nested = export_dir / 'nested'
                nested.mkdir()

                with override_settings(
                    MEDIA_ROOT=directory, MEDIA_URL='/media/', USE_TZ=use_tz,
                    TIME_ZONE='Asia/Shanghai',
                ), patch.object(case_result.time, 'time', return_value=self.now):
                    result = case_result._export_api_case_result_value(
                        {'items': [1, 2]}, case_id=1, step_id=2, scenario_id=3, json_path='$.data',
                    )

                self.assertFalse(expired.exists())
                self.assertTrue(boundary.exists())
                self.assertTrue(recent.exists())
                self.assertTrue(unrelated.exists())
                self.assertTrue(nested.is_dir())
                payload = json.loads(Path(result['file_path']).read_text(encoding='utf-8'))
                self.assertEqual(payload['value'], {'items': [1, 2]})
                self.assertEqual(result['retention_days'], 7)
                self.assertTrue(result['download_url'].startswith('/media/mcp_export/api_case_result/'))

    def test_cleanup_tolerates_missing_directory(self):
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            case_result._cleanup_api_case_result_exports()
            self.assertFalse((Path(directory) / case_result.API_CASE_RESULT_EXPORT_RELATIVE_DIR).exists())

    def test_cleanup_continues_when_a_file_is_unavailable(self):
        with tempfile.TemporaryDirectory() as directory:
            export_dir = Path(directory) / case_result.API_CASE_RESULT_EXPORT_RELATIVE_DIR
            unavailable = self.create_file(export_dir / 'unavailable.json', self.now - self.retention_seconds - 1)
            expired = self.create_file(export_dir / 'expired.json', self.now - self.retention_seconds - 1)
            original_getmtime = os.path.getmtime

            def getmtime(path):
                if Path(path) == unavailable:
                    raise OSError('file unavailable')
                return original_getmtime(path)

            with override_settings(MEDIA_ROOT=directory), \
                    patch.object(case_result.time, 'time', return_value=self.now), \
                    patch.object(case_result.os.path, 'getmtime', side_effect=getmtime):
                case_result._cleanup_api_case_result_exports()

            self.assertTrue(unavailable.exists())
            self.assertFalse(expired.exists())
