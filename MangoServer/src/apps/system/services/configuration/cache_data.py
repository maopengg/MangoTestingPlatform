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
    @staticmethod
    def replace_retired_datasource_policy(config, value):
        """只供维护窗口的退役事务使用；连接与历史占用由调用方完整校验。"""
        import json
        from src.apps.system.services.configuration.system_config import SystemConfigService
        error = SystemConfigService.validate_editable_config(config.key, value)
        if config.key != 'DATASOURCE_PERFORMANCE_POLICY' or error:
            raise SystemError(SYSTEM_UPDATE_VALIDATION_FAILED, value=(error or '配置键不匹配',))
        config.value = json.dumps(value)
        config.save(update_fields=['value', 'update_time'])
        transaction.on_commit(lambda: SystemConfigService.invalidate(config.key))

    @classmethod
    @transaction.atomic
    def update_datasource_policy(cls, changes: dict, *, update_user_id: int):
        """运维使用与配置页面相同的结构及过渡校验，禁止绕过在途连接保护。"""
        import json
        from src.apps.system.services.configuration.system_config import SystemConfigService
        config = CacheData.objects.select_for_update().get(key='DATASOURCE_PERFORMANCE_POLICY')
        previous = SystemConfigService.cast_value(config.value, config.value_type, {})
        value = {**previous, **changes}
        error = (SystemConfigService.validate_editable_config(config.key, value)
                 or SystemConfigService.validate_datasource_policy_transition(config, value))
        if error:
            raise SystemError(SYSTEM_UPDATE_VALIDATION_FAILED, value=(error,))
        config.value = json.dumps(value, ensure_ascii=False)
        config.update_user_id = update_user_id
        config.save(update_fields=['value', 'update_user', 'update_time'])
        SystemConfigService.invalidate(config.key)
        return value

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
