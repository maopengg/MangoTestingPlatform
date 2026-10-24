from io import BytesIO
from unittest.mock import patch

from django.http import FileResponse
from django.test import SimpleTestCase
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from src.apps.test_center.api.views.execution_result import ExecutionResultViews


class ExecutionResultContentViewTests(SimpleTestCase):
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
