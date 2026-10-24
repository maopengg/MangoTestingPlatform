import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock, patch

import httpx

from src.network.http.apis.base import ApiError as HttpApiError
from src.network.http.apis.system import SystemApi


class FileUploadErrorTest(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as file_obj:
            file_obj.write(b'picture')
            self.file_path = file_obj.name
        self.client = SimpleNamespace(post=AsyncMock())
        self.api = SystemApi(
            self.client,
            SimpleNamespace(get_headers=lambda: {'Authorization': 'masked'}),
        )

    def tearDown(self):
        if os.path.exists(self.file_path):
            os.remove(self.file_path)

    async def test_storage_error_preserves_server_reason(self):
        self.client.post.return_value = {
            'code': 1004,
            'msg': '执行产物保存失败：TOS存储桶不存在或访问路径错误',
            'data': None,
        }

        result = await self.api.upload_file(self.file_path, 'failure.jpg')

        self.assertFalse(result.success)
        self.assertEqual(result.error_type, 'storage')
        self.assertIn('TOS存储桶不存在', result.error_message)
        self.client.post.assert_awaited_once()

    async def test_success_without_path_reports_invalid_response(self):
        self.client.post.return_value = {'code': 200, 'msg': '成功', 'data': None}

        result = await self.api.upload_file(self.file_path, 'failure.jpg')

        self.assertFalse(result.success)
        self.assertEqual(result.error_type, 'invalid_response')

    async def test_connection_error_is_retried_and_classified(self):
        request = httpx.Request('POST', 'http://platform.example/api/system/file')
        self.client.post.side_effect = httpx.ConnectError('connect failed', request=request)

        with patch('src.network.http.apis.system.asyncio.sleep', new=AsyncMock()):
            result = await self.api.upload_file(self.file_path, 'failure.jpg')

        self.assertFalse(result.success)
        self.assertEqual(result.error_type, 'connection')
        self.assertEqual(self.client.post.await_count, 3)

    async def test_http_auth_error_reports_login_failure(self):
        self.client.post.side_effect = HttpApiError('sensitive response body', status_code=401)
        self.api._refresh_upload_auth = AsyncMock(return_value=False)

        result = await self.api.upload_file(self.file_path, 'failure.jpg')

        self.assertFalse(result.success)
        self.assertEqual(result.error_type, 'authentication')
        self.assertNotIn('sensitive', result.error_message)
        self.api._refresh_upload_auth.assert_awaited_once()


class FileDownloadLoopTest(unittest.IsolatedAsyncioTestCase):

    async def test_isolated_download_uses_and_closes_fresh_client(self):
        original_client = SimpleNamespace(
            base_url='https://platform.example/api/',
            proxy=None,
        )
        auth = SimpleNamespace(get_headers=lambda: {'Authorization': 'masked'})
        api = SystemApi(original_client, auth)
        isolated_client = SimpleNamespace(close=AsyncMock())
        download = AsyncMock(return_value='/tmp/example.docx')

        with (
            patch(
                'src.network.http.apis.system.BaseHttpClient',
                return_value=isolated_client,
            ) as client_factory,
            patch.object(SystemApi, 'download_file_by_id', new=download),
        ):
            result = await api.download_file_by_id_isolated(178)

        self.assertEqual(result, '/tmp/example.docx')
        client_factory.assert_called_once_with(
            base_url='https://platform.example/api/',
            headers={'Authorization': 'masked'},
            proxy=None,
            logger=ANY,
        )
        download.assert_awaited_once_with(178)
        isolated_client.close.assert_awaited_once()


if __name__ == '__main__':
    unittest.main()
