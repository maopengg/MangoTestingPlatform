import gzip
import json
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings

from src.apps.test_center.services.results.execution_result import ExecutionResultService as Results
from src.apps.test_center.services.results.result_file import ExecutionResultFileService as Files


@override_settings(RESULT_DATA_TO_FILE=True, RESULT_DATA_DETAIL_INLINE_MAX_SIZE=1000)
class ResultGzipTests(SimpleTestCase):
    payload = {'steps': [{'response': {'json': {'name': '中文响应', 'rows': ['example'] * 1000}}}]}

    def raw(self):
        return json.dumps(self.payload, ensure_ascii=False, separators=(',', ':')).encode()

    def item(self, **kwargs):
        fields = dict(id=1, target_type='api_case', result_data=None, result_cleaned=False,
            result_object_key='result/example.json.gz', result_size=len(Files.encode(self.raw())))
        fields.update(kwargs)
        return SimpleNamespace(**fields)

    def test_new_file_is_gzip_and_size_is_actual_stored_bytes(self):
        stored = {}
        def save(name, content):
            stored[name] = content.read()
            return name
        with patch('src.apps.test_center.services.results.execution_result.default_storage.save', side_effect=save):
            result = Results.prepare_result_payload(self.payload, 'api_case', 1)
        self.assertTrue(result['result_object_key'].endswith('.json.gz'))
        encoded = stored[result['result_object_key']]
        self.assertEqual(gzip.decompress(encoded), self.raw())
        self.assertEqual(result['result_size'], len(encoded))
        self.assertLess(result['result_size'], len(self.raw()))
        self.assertEqual(result['result_checksum'], Results.calc_result_checksum(self.payload))

    def test_load_accepts_old_json_and_gzip_by_magic_not_extension(self):
        for key in ('old.json', 'new.json.gz'):
            for raw in (self.raw(), Files.encode(self.raw())):
                source = BytesIO(raw)
                with self.subTest(key=key, gzip=raw.startswith(b'\x1f\x8b')), patch(
                    'src.apps.test_center.services.results.execution_result.default_storage.open', return_value=source):
                    self.assertEqual(Results.load_result_data(self.item(result_object_key=key)), self.payload)
                    self.assertTrue(source.closed)

    def test_corrupt_empty_and_truncated_files_are_not_valid_results(self):
        for raw in (b'', b'invalid-json', b'\x1f\x8binvalid', Files.encode(self.raw())[:-5]):
            with self.subTest(raw=raw[:3]), patch(
                'src.apps.test_center.services.results.execution_result.default_storage.open', return_value=BytesIO(raw)):
                self.assertIsNone(Results.load_result_data(self.item()))

    def test_cleaned_inline_and_empty_results_do_not_open_storage(self):
        with patch('src.apps.test_center.services.results.execution_result.default_storage.open') as opened:
            self.assertIsNone(Results.load_result_data(self.item(result_cleaned=True)))
            self.assertIsNone(Results.load_result_data(self.item(result_object_key=None)))
            self.assertEqual(Results.load_result_data(self.item(result_data=self.payload)), self.payload)
        opened.assert_not_called()

    @override_settings(RESULT_DATA_TO_FILE=False)
    def test_inline_storage_keeps_existing_json_and_size(self):
        with patch('src.apps.test_center.services.results.execution_result.default_storage.save') as save:
            result = Results.prepare_result_payload(self.payload, 'api_case', 1)
        save.assert_not_called()
        self.assertEqual(result['result_data'], self.payload)
        self.assertEqual(result['result_size'], len(self.raw()))

    def test_read_limit_applies_after_decompression_and_closes_source(self):
        source = BytesIO(Files.encode(self.raw()))
        raw = Files.read(source, limit=100)
        self.assertEqual(len(raw), 101)
        self.assertTrue(source.closed)

    def test_mcp_large_json_keeps_uncompressed_inline_limit(self):
        with patch.object(Results, 'serialize_summary', return_value={}), patch(
            'src.apps.test_center.services.results.execution_result.default_storage.open',
            return_value=BytesIO(Files.encode(self.raw()))), patch.object(Results, 'result_download_url', return_value='file'):
            result = Results.serialize_detail(self.item())
        self.assertTrue(result['result_too_large'])
        self.assertEqual(result['result_compression'], 'gzip')
        self.assertIsNone(result['result_data'])

    @override_settings(RESULT_DATA_DETAIL_INLINE_MAX_SIZE=100000)
    def test_mcp_small_gzip_returns_original_json(self):
        with patch.object(Results, 'serialize_summary', return_value={}), patch(
            'src.apps.test_center.services.results.execution_result.default_storage.open',
            return_value=BytesIO(Files.encode(self.raw()))):
            result = Results.serialize_detail(self.item())
        self.assertFalse(result['result_too_large'])
        self.assertEqual(result['result_data'], self.payload)

    def test_page_prefers_compressed_file_without_reading_json(self):
        with patch.object(Results, 'serialize_summary', return_value={}), patch.object(
            Results, 'read_result_file') as read, patch.object(Results, 'result_download_url', return_value='file'):
            result = Results.serialize_detail(self.item(), prefer_file=True)
        read.assert_not_called()
        self.assertTrue(result['result_too_large'])

    def test_accepted_encodings_respect_q_zero_and_wildcard(self):
        for header in ('gzip', 'br, gzip;q=0.5', '*;q=1', 'GZIP'):
            self.assertTrue(Files.accepts_gzip(header))
        for header in (None, '', 'identity', 'gzip;q=0, *;q=1', 'gzip;q=invalid', 'gzip;q=2'):
            self.assertFalse(Files.accepts_gzip(header))

    def test_report_rewrite_uses_compressed_size_not_old_raw_size(self):
        from src.apps.test_center.services.reporting.test_suite.detail_result import TestSuiteExecutionResultService
        item = self.item(target_id=1, test_suite_id=2, test_suite_detail_id=3, save=Mock())
        prepared = dict(result_data=None, result_object_key='new.json.gz', result_file_name='new.json.gz',
            result_size=100, result_checksum='checksum')
        with patch.object(Results, 'prepare_result_payload', return_value=prepared), patch(
            'src.apps.test_center.services.reporting.test_suite.detail_result.default_storage.delete'):
            TestSuiteExecutionResultService.update_payload_result_data(item, self.payload, result_size=9999)
        self.assertEqual(item.result_size, 100)
