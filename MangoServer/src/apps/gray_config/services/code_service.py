# -*- coding: utf-8 -*-
from django.utils import timezone

from src.apps.gray_config.enums import GrayActionEnum, GrayExecutionStatusEnum
from src.apps.gray_config.exceptions import (
    GRAY_SQL_CONFIG_GRAY_REQUIRED,
    GRAY_CODE_GRAY_INVALID,
    GRAY_CODE_EXECUTION_GRAY_FAILED,
    GrayConfigError,
)
from src.apps.gray_config.models import GrayExecutionLog, GrayFeature


class GrayCodeService:
    @classmethod
    def preview_feature(cls, feature: GrayFeature, target_value: str | None, action: str) -> dict:
        code = cls.resolve_code(feature, action)
        context = cls.build_context(feature, target_value, action)
        return {
            "feature_id": feature.id,
            "feature_key": feature.feature_key,
            "target_value": target_value,
            "action": action,
            "before_text": code,
            "after_text": code,
            "config_type": "code",
            "context": context,
        }

    @classmethod
    def execute_feature(
            cls,
            feature: GrayFeature,
            target_value: str | None,
            action: str,
            gray_config_id: int | None = None,
            case_snapshot: dict | None = None,
    ) -> GrayExecutionLog:
        code = cls.resolve_code(feature, action)
        context = cls.build_context(feature, target_value, action)
        log = GrayExecutionLog.objects.create(
            gray_config_id=gray_config_id,
            gray_feature=feature,
            config_type=feature.config_type,
            feature_key=feature.feature_key,
            target_value=target_value,
            action=action,
            before_snapshot={"code": code, "context": context},
            status=GrayExecutionStatusEnum.WAITING.value,
            started_at=timezone.now(),
            **(case_snapshot or {}),
        )
        try:
            result = cls.run_code(code, context)
            log.after_snapshot = {"result": result}
            log.status = GrayExecutionStatusEnum.SUCCESS.value
        except Exception as error:
            log.status = GrayExecutionStatusEnum.FAILED.value
            log.error_message = str(error)
        finally:
            log.finished_at = timezone.now()
            log.save()
        return log

    @staticmethod
    def resolve_code(feature: GrayFeature, action: str) -> str:
        if action == GrayActionEnum.ENABLE.value:
            code = feature.enable_code
        elif action == GrayActionEnum.DISABLE.value:
            code = feature.disable_code
        else:
            code = feature.restore_code or feature.disable_code
        if not code:
            raise GrayConfigError(GRAY_SQL_CONFIG_GRAY_REQUIRED)
        return code

    @staticmethod
    def build_context(feature: GrayFeature, target_value: str | None, action: str) -> dict:
        return {
            "feature_id": feature.id,
            "feature_key": feature.feature_key,
            "target_value": target_value or "",
            "action": action,
            "project_product_id": feature.project_product_id,
            "module_id": feature.module_id,
        }

    @staticmethod
    def run_code(code: str, context: dict):
        namespace = {}
        try:
            exec(code, namespace)
        except Exception as error:
            raise GrayConfigError(GRAY_CODE_EXECUTION_GRAY_FAILED, value=(str(error),)) from error
        gray_func = namespace.get("gray")
        if not callable(gray_func):
            raise GrayConfigError(GRAY_CODE_GRAY_INVALID)
        try:
            result = gray_func(context)
        except Exception as error:
            raise GrayConfigError(GRAY_CODE_EXECUTION_GRAY_FAILED, value=(str(error),)) from error
        return result if isinstance(result, dict) else {"result": result}
