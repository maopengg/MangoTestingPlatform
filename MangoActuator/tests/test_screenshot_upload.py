import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from mangoautomation.models import ElementResultModel

from src.models.socket_model import FileUploadResultModel
from src.services.ui.page_steps import PageSteps


class ScreenshotUploadTest(unittest.IsolatedAsyncioTestCase):

    @staticmethod
    def page_steps():
        instance = PageSteps.__new__(PageSteps)
        instance.page_step_result_model = SimpleNamespace(status=0, error_message='执行失败')
        return instance

    async def test_successful_upload_replaces_local_path_and_deletes_file(self):
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as file_obj:
            local_path = file_obj.name
        result = ElementResultModel(
            id=1,
            type=0,
            picture_name='failure.jpg',
            picture_path=local_path,
        )

        with patch(
                'src.services.ui.page_steps.HTTP.system.upload_file',
                new=AsyncMock(return_value=FileUploadResultModel(
                    success=True,
                    path='bucket/screenshot/failure.jpg',
                )),
        ):
            await self.page_steps()._upload_element_picture(result)

        self.assertEqual(result.picture_path, 'bucket/screenshot/failure.jpg')
        self.assertFalse(os.path.exists(local_path))

    async def test_failed_upload_keeps_specific_reason(self):
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as file_obj:
            local_path = file_obj.name
        result = ElementResultModel(
            id=1,
            type=0,
            picture_name='failure.jpg',
            picture_path=local_path,
        )
        instance = self.page_steps()

        with patch(
                'src.services.ui.page_steps.HTTP.system.upload_file',
                new=AsyncMock(return_value=FileUploadResultModel(
                    success=False,
                    error_type='storage',
                    error_message='执行产物保存失败：TOS鉴权失败，请检查访问凭证及存储桶写入权限',
                )),
        ):
            await instance._upload_element_picture(result)

        self.assertIsNone(result.picture_path)
        self.assertIn('TOS鉴权失败', instance.page_step_result_model.error_message)
        self.assertTrue(os.path.exists(local_path))
        os.remove(local_path)

    async def test_missing_local_file_does_not_return_local_path(self):
        result = ElementResultModel(
            id=1,
            type=0,
            picture_name='missing.jpg',
            picture_path='/tmp/mango-missing-screenshot.jpg',
        )

        await self.page_steps()._upload_element_picture(result)

        self.assertIsNone(result.picture_path)


if __name__ == '__main__':
    unittest.main()
