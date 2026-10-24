"""系统缓存配置写入服务。"""

from django.db import transaction

from src.apps.system.exceptions import (
    SYSTEM_SAVE_VALIDATION_FAILED,
    SYSTEM_UPDATE_VALIDATION_FAILED,
    SystemError,
)
from src.apps.system.models import CacheData
from src.common.database import ModelMutationValidationError, save_model


class CacheDataService:
    @classmethod
    @transaction.atomic
    def upsert_unique_key(cls, key: str, payload: dict) -> CacheData:
        matches = CacheData.objects.select_for_update().filter(key=key).order_by("id")
        instance = matches.first()
        if instance is None:
            error_definition = SYSTEM_SAVE_VALIDATION_FAILED
        else:
            matches.exclude(id=instance.id).delete()
            error_definition = SYSTEM_UPDATE_VALIDATION_FAILED
        try:
            return save_model(
                CacheData,
                payload,
                instance=instance,
                partial=instance is not None,
            )
        except ModelMutationValidationError as error:
            raise SystemError(error_definition, value=(error.errors,)) from error
