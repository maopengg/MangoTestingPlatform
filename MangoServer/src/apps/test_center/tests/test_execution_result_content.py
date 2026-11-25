from io import BytesIO
import gzip
from unittest.mock import patch

from django.http import FileResponse
from django.test import SimpleTestCase
from django.middleware.gzip import GZipMiddleware
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from src.apps.test_center.api.views.execution_result import ExecutionResultViews


class ExecutionResultContentViewTests(SimpleTestCase):
    def compressed_response(self, accept_encoding):
        source = BytesIO(gzip.compress(b'{"status":1}'))
        request = Request(APIRequestFactory().get('/api/system/execution/result/content',
            {'id': 123}, HTTP_ACCEPT_ENCODING=accept_encoding))
        with patch('src.apps.test_center.api.views.execution_result.ExecutionResultService.visible_results'), patch(
            'src.apps.test_center.api.views.execution_result.ExecutionResultService.open_result_file',
            return_value=(source, 'result.json.gz')):
            response = ExecutionResultViews().get_content(request)
        return source, request, response

    def test_gzip_is_transferred_as_is_and_browser_can_decode_it(self):
        source, request, response = self.compressed_response('gzip, deflate, br')
        response = GZipMiddleware(lambda request: response).process_response(request, response)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertEqual(response['Content-Encoding'], 'gzip')
        self.assertIn('Accept-Encoding', response['Vary'])
        self.assertIn('private', response['Cache-Control'])
        self.assertEqual(response['Content-Disposition'], 'inline; filename="result.json"')
        payload = b''.join(response.streaming_content)
        self.assertEqual(gzip.decompress(payload), b'{"status":1}')
        self.assertEqual(int(response['Content-Length']), len(payload))
        response.close()
        self.assertTrue(source.closed)

    def test_client_without_gzip_receives_streamed_legacy_json(self):
        for encoding in ('identity', 'gzip;q=0'):
            source, _, response = self.compressed_response(encoding)
            self.assertNotIn('Content-Encoding', response)
            self.assertEqual(b''.join(response.streaming_content), b'{"status":1}')
            response.close()
            self.assertTrue(source.closed)

    @patch('src.apps.test_center.api.views.execution_result.ExecutionResultService.visible_results')
    @patch(
        'src.apps.test_center.api.views.execution_result.ExecutionResultService.open_result_file',
        return_value=(BytesIO(b'{"status":1}'), 'result.json'),
    )
    def test_content_is_streamed_through_same_origin_api(self, open_result_file, visible_results):
        request = Request(APIRequestFactory().get(
            '/api/system/execution/result/content',
            {'id': 123},
        ))

        response = ExecutionResultViews().get_content(request)

        self.assertIsInstance(response, FileResponse)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertEqual(b''.join(response.streaming_content), b'{"status":1}')
        open_result_file.assert_called_once_with(123, queryset=visible_results.return_value)
