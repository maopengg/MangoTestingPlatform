"""测试文件写入服务。"""

from django.db import transaction

from src.apps.test_center.exceptions import TEST_FILE_NOT_FOUND, TestCenterError
from src.apps.test_center.models import FileData
from src.common.database import ModelMutationValidationError, save_model
from src.common.exceptions import SAVE_VALIDATION_FAILED


class FileDataService:
    @staticmethod
    def get_instance(file_id: int) -> FileData:
        try:
            return FileData.objects.get(id=file_id)
        except FileData.DoesNotExist as error:
            raise TestCenterError(
                TEST_FILE_NOT_FOUND,
                details={"file_id": file_id},
            ) from error

    @classmethod
    @transaction.atomic
    def create(cls, payload: dict) -> FileData:
        try:
            return save_model(FileData, payload)
        except ModelMutationValidationError as error:
            raise TestCenterError(SAVE_VALIDATION_FAILED, value=(error.errors,)) from error
