from datetime import timedelta

from django.utils import timezone

from src.apps.gray_config.enums import GrayActionEnum, GrayCaseTypeEnum, GrayExecutionStatusEnum
from src.apps.gray_config.exceptions import (
    GRAY_RECORD_EXECUTION_GRAY_NOT_FOUND,
    GRAY_RECORD_EXECUTION_GRAY_REQUIRED,
    GrayConfigError,
)
from src.apps.gray_config.models import GrayExecutionLog
from src.apps.gray_config.services.feature import GrayFeatureService


class GrayExecutionLogService:
    DEFAULT_RETENTION_DAYS = 30

    @classmethod
    def retry_restore(cls, execution_log_id: int) -> GrayExecutionLog:
        try:
            source_log = GrayExecutionLog.objects.select_related(
                "gray_feature",
                "yaml_file_binding",
                "yaml_file_binding__repository",
            ).get(id=execution_log_id)
        except GrayExecutionLog.DoesNotExist as exc:
            raise GrayConfigError(GRAY_RECORD_EXECUTION_GRAY_NOT_FOUND) from exc
        if not source_log.gray_feature_id:
            raise GrayConfigError(GRAY_RECORD_EXECUTION_GRAY_REQUIRED)
        test_env = source_log.yaml_file_binding.repository.test_env if source_log.yaml_file_binding_id else None
        variable_source = cls.restore_variable_source(source_log)
        restore_log = GrayFeatureService.execute(
            source_log.gray_feature_id,
            source_log.target_value,
            cls.restore_action(source_log.action),
            source_log.gray_config_id,
            variable_source,
            None,
            test_env,
        )
        cls.update_source_restore_status(source_log, restore_log)
        return restore_log

    @staticmethod
    def restore_action(action: str) -> str:
        if action == GrayActionEnum.DISABLE.value:
            return GrayActionEnum.ENABLE.value
        return GrayActionEnum.RESTORE.value

    @classmethod
    def restore_variable_source(cls, source_log: GrayExecutionLog) -> str | None:
        if source_log.case_type == GrayCaseTypeEnum.API.value:
            return "api"
        if source_log.case_type == GrayCaseTypeEnum.UI.value:
            return "ui"
        if cls.gray_feature_has_variable(source_log):
            return "api"
        return None

    @staticmethod
    def gray_feature_has_variable(source_log: GrayExecutionLog) -> bool:
        path_config = getattr(source_log.gray_feature, "path_config", None)
        if not isinstance(path_config, list):
            return False
        for item in path_config:
            if not isinstance(item, dict):
                continue
            for key in ("original_value", "value"):
                value = item.get(key)
                if isinstance(value, str) and ("${{" in value or "${" in value):
                    return True
        return False

    @staticmethod
    def case_snapshot(source_log: GrayExecutionLog) -> dict:
        return {
            "test_suite_id": source_log.test_suite_id,
            "test_suite_detail_id": source_log.test_suite_detail_id,
            "case_type": source_log.case_type,
            "case_id": source_log.case_id,
            "case_name": source_log.case_name,
            "api_case_detailed_id": source_log.api_case_detailed_id,
            "api_case_detailed_name": source_log.api_case_detailed_name,
            "api_case_detailed_parameter_id": source_log.api_case_detailed_parameter_id,
            "api_case_detailed_parameter_name": source_log.api_case_detailed_parameter_name,
        }

    @staticmethod
    def update_source_restore_status(source_log: GrayExecutionLog, restore_log: GrayExecutionLog):
        source_log.restore_commit_hash = restore_log.commit_hash
        if restore_log.status == GrayExecutionStatusEnum.SUCCESS.value:
            source_log.status = GrayExecutionStatusEnum.RESTORED.value
            source_log.error_message = None
        else:
            source_log.status = GrayExecutionStatusEnum.RESTORE_FAILED.value
            source_log.error_message = restore_log.error_message
        source_log.save(update_fields=["restore_commit_hash", "status", "error_message", "update_time"])

    @classmethod
    def cleanup_expired(cls, retention_days: int = DEFAULT_RETENTION_DAYS) -> int:
        cutoff_time = timezone.now() - timedelta(days=retention_days)
        return GrayExecutionLog.objects.filter(create_time__lt=cutoff_time).delete()[0]
