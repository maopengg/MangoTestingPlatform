# -*- coding: utf-8 -*-
from __future__ import annotations

import time
from mangotools.enums import StatusEnum

from src.apps.gray_config.enums import GrayActionEnum, GrayCaseScopeEnum, GrayCaseTypeEnum, GrayExecutionStatusEnum
from src.apps.gray_config.exceptions import (
    GRAY_EXECUTION_GRAY_FAILED,
    GRAY_EXECUTION_GRAY_FAILED_CODE_EXECUTION_GRAY_FAILED,
    GrayConfigError,
)
from src.apps.gray_config.models import AutomationCaseGrayConfig, GrayExecutionLog
from src.apps.gray_config.services.feature import GrayFeatureService
from src.apps.gray_config.services.lock import GrayExecutionLockService, GrayLockResource
from src.common.logging import log


class GrayCaseExecutionRunner:
    @classmethod
    def apply_api_case(
            cls,
            api_case,
            test_suite_id: int | None = None,
            test_suite_detail_id: int | None = None,
            test_env: int | str | None = None,
    ) -> list:
        if hasattr(api_case, "_revision_gray_configs"):
            return cls.apply_configs(
                api_case._revision_gray_configs,
                cls.api_case_snapshot(api_case, test_suite_id, test_suite_detail_id, test_env=test_env),
            )
        return cls.apply_configs(
            AutomationCaseGrayConfig.objects.select_related("gray_feature", "gray_feature__yaml_file").filter(
                case_type=GrayCaseTypeEnum.API.value,
                scope=GrayCaseScopeEnum.CASE.value,
                api_case_id=api_case.id,
                status=StatusEnum.SUCCESS.value,
            ).order_by("sort", "id"),
            cls.api_case_snapshot(api_case, test_suite_id, test_suite_detail_id, test_env=test_env),
        )

    @classmethod
    def apply_api_parameter(
            cls,
            api_case,
            case_detailed,
            parameter,
            test_suite_id: int | None = None,
            test_suite_detail_id: int | None = None,
            inherited_configs: list | None = None,
            test_env: int | str | None = None,
    ) -> list:
        if hasattr(parameter, "_revision_gray_configs"):
            return cls.apply_configs(
                parameter._revision_gray_configs,
                cls.api_case_snapshot(
                    api_case,
                    test_suite_id,
                    test_suite_detail_id,
                    case_detailed,
                    parameter,
                    test_env,
                ),
                inherited_configs=inherited_configs,
            )
        queryset = AutomationCaseGrayConfig.objects.select_related("gray_feature", "gray_feature__yaml_file").filter(
            case_type=GrayCaseTypeEnum.API.value,
            scope=GrayCaseScopeEnum.API_PARAMETER.value,
            status=StatusEnum.SUCCESS.value,
            api_case_detailed_parameter_id=parameter.id,
        )
        return cls.apply_configs(
            queryset.order_by("sort", "id"),
            cls.api_case_snapshot(api_case, test_suite_id, test_suite_detail_id, case_detailed, parameter, test_env),
            inherited_configs=inherited_configs,
        )

    @classmethod
    def apply_ui_case(
            cls,
            ui_case,
            test_suite_id: int | None = None,
            test_suite_detail_id: int | None = None,
            test_env: int | str | None = None,
    ) -> list:
        return cls.apply_configs(
            AutomationCaseGrayConfig.objects.select_related("gray_feature", "gray_feature__yaml_file").filter(
                case_type=GrayCaseTypeEnum.UI.value,
                scope=GrayCaseScopeEnum.CASE.value,
                ui_case_id=ui_case.id,
                status=StatusEnum.SUCCESS.value,
            ).order_by("sort", "id"),
            {
                "test_suite_id": test_suite_id,
                "test_suite_detail_id": test_suite_detail_id,
                "case_type": GrayCaseTypeEnum.UI.value,
                "case_id": ui_case.id,
                "case_name": ui_case.name,
                "_test_env": test_env,
            },
        )

    @classmethod
    def apply_configs(cls, configs, case_snapshot: dict, inherited_configs: list | None = None) -> list:
        applied = []
        inherited_keys = cls.config_keys(inherited_configs or [])
        active_configs = [config for config in list(configs) if cls.config_key(config) not in inherited_keys]
        locks = []
        lock_resources = []
        try:
            cls.prepare_runtime_features(active_configs, case_snapshot)
            lock_resources = cls.lock_resources(active_configs, case_snapshot)
            locks = GrayExecutionLockService.acquire_resources(
                lock_resources,
                renew=case_snapshot.get("case_type") != GrayCaseTypeEnum.UI.value,
            )
            cls.attach_locks(active_configs, locks, lock_resources)
            for config in active_configs:
                log = GrayFeatureService.execute(
                    config.gray_feature_id,
                    config.target_value,
                    config.action or GrayActionEnum.ENABLE.value,
                    config.id,
                    cls.variable_source(case_snapshot),
                    test_env=case_snapshot.get("_test_env"),
                    use_lock=False,
                )
                cls.bind_execution_log_to_lock(lock_resources, log)
                cls.update_log_case_snapshot(log, case_snapshot)
                if log.status != GrayExecutionStatusEnum.SUCCESS.value:
                    if log.error_message:
                        raise GrayConfigError(GRAY_EXECUTION_GRAY_FAILED_CODE_EXECUTION_GRAY_FAILED,
                                              value=(log.error_message,))
                    raise GrayConfigError(GRAY_EXECUTION_GRAY_FAILED)
                config._gray_execution_log_id = log.id
                applied.append(config)
                wait_seconds = cls.resolve_wait_seconds(config)
                if wait_seconds:
                    time.sleep(max(0, int(wait_seconds)))
            return applied
        except Exception:
            try:
                cls.restore_configs(applied, case_snapshot)
            finally:
                if not applied:
                    GrayExecutionLockService.release_handles(locks)
                else:
                    cls.release_config_locks(applied)
            raise

    @staticmethod
    def config_key(config) -> tuple:
        return (
            config.gray_feature_id,
            str(config.target_value),
            config.action or GrayActionEnum.ENABLE.value,
        )

    @staticmethod
    def resolve_wait_seconds(config) -> int:
        if config.wait_seconds:
            return config.wait_seconds
        gray_feature = getattr(config, "gray_feature", None)
        yaml_file = getattr(gray_feature, "yaml_file", None)
        if yaml_file and yaml_file.effect_wait_seconds:
            return yaml_file.effect_wait_seconds
        return 0

    @staticmethod
    def restore_action(config) -> str:
        if (config.action or GrayActionEnum.ENABLE.value) == GrayActionEnum.DISABLE.value:
            return GrayActionEnum.ENABLE.value
        return GrayActionEnum.RESTORE.value

    @classmethod
    def config_keys(cls, configs: list) -> set[tuple]:
        return {cls.config_key(config) for config in configs or []}

    @classmethod
    def restore_configs(cls, configs: list, case_snapshot: dict):
        try:
            for config in reversed(configs or []):
                if not config.restore_after_execute:
                    continue
                try:
                    restore_log = GrayFeatureService.execute(
                        config.gray_feature_id,
                        config.target_value,
                        cls.restore_action(config),
                        config.id,
                        cls.variable_source(case_snapshot),
                        test_env=case_snapshot.get("_test_env"),
                        use_lock=False,
                    )
                    cls.update_log_case_snapshot(restore_log, case_snapshot)
                    cls.update_source_restore_status(config, restore_log)
                except Exception as error:
                    cls.mark_source_restore_failed(config, str(error))
                    log.system.error(
                        f"灰度恢复失败：config_id={getattr(config, 'id', None)}, "
                        f"feature_id={getattr(config, 'gray_feature_id', None)}, error={error}"
                    )
        finally:
            cls.release_config_locks(configs)

    @classmethod
    def restore_by_config_ids(
            cls,
            config_ids: list[int] | None,
            case_snapshot: dict,
            execution_log_ids: list[int] | None = None,
    ):
        if not config_ids:
            return
        configs = list(
            AutomationCaseGrayConfig.objects.select_related("gray_feature", "gray_feature__yaml_file").filter(
                id__in=config_ids,
                status=StatusEnum.SUCCESS.value,
            ).order_by("sort", "id")
        )
        source_log_map = {
            int(config_id): log_id
            for config_id, log_id in zip(config_ids, execution_log_ids or [])
            if config_id and log_id
        }
        for config in configs:
            source_log_id = source_log_map.get(config.id)
            if source_log_id:
                config._gray_execution_log_id = source_log_id
        cls.attach_rebuilt_lock_resources(configs, case_snapshot, source_log_map)
        cls.restore_configs(configs, case_snapshot)

    @classmethod
    def prepare_runtime_features(cls, configs: list, case_snapshot: dict):
        for config in configs or []:
            config.gray_feature = GrayFeatureService.resolve_runtime_feature(
                config.gray_feature_id,
                case_snapshot.get("_test_env"),
            )

    @classmethod
    def lock_resources(cls, configs: list, case_snapshot: dict) -> list[GrayLockResource]:
        owner_type, owner_id = cls.lock_owner(case_snapshot)
        return [
            GrayExecutionLockService.resource_for_feature(
                config.gray_feature,
                owner_type=owner_type,
                owner_id=owner_id,
                remark=cls.lock_remark(case_snapshot),
            )
            for config in configs or []
        ]

    @staticmethod
    def lock_owner(case_snapshot: dict) -> tuple[str, str]:
        case_type = case_snapshot.get("case_type") or "-"
        if case_snapshot.get("api_case_detailed_parameter_id"):
            return f"{case_type}:api_parameter", str(case_snapshot.get("api_case_detailed_parameter_id"))
        if case_snapshot.get("api_case_detailed_id"):
            return f"{case_type}:api_step", str(case_snapshot.get("api_case_detailed_id"))
        return f"{case_type}:case", str(case_snapshot.get("case_id") or "-")

    @staticmethod
    def lock_remark(case_snapshot: dict) -> str:
        return str(case_snapshot.get("case_name") or case_snapshot.get("api_case_detailed_parameter_name") or "")[:512]

    @staticmethod
    def attach_locks(configs: list, locks: list, lock_resources: list[GrayLockResource]):
        for config in configs or []:
            config._gray_lock_handles = locks
            config._gray_lock_resources = lock_resources

    @classmethod
    def attach_rebuilt_lock_resources(cls, configs: list, case_snapshot: dict, source_log_map: dict[int, int]):
        owner_type, owner_id = cls.lock_owner(case_snapshot)
        logs = GrayExecutionLog.objects.select_related("repository", "gray_feature").filter(
            id__in=[item for item in source_log_map.values() if item]
        )
        log_map = {item.id: item for item in logs}
        for config in configs or []:
            source_log = log_map.get(source_log_map.get(config.id))
            if not source_log:
                continue
            config._gray_lock_resources = [
                cls.lock_resource_from_log(source_log, owner_type, owner_id, cls.lock_remark(case_snapshot))
            ]

    @staticmethod
    def lock_resource_from_log(log_item: GrayExecutionLog, owner_type: str, owner_id: str,
                               remark: str) -> GrayLockResource:
        if log_item.repository_id:
            branch = log_item.target_branch or log_item.repository.branch or "master"
            return GrayLockResource(
                lock_key=f"gray_repo:{log_item.repository_id}:{branch}",
                repository=log_item.repository,
                branch=branch,
                owner_type=owner_type,
                owner_id=owner_id,
                execution_log_id=log_item.id,
                remark=remark,
            )
        feature = log_item.gray_feature
        return GrayExecutionLockService.resource_for_feature(
            feature,
            owner_type=owner_type,
            owner_id=owner_id,
            execution_log_id=log_item.id,
            remark=remark,
        )

    @staticmethod
    def bind_execution_log_to_lock(lock_resources: list[GrayLockResource], log_item: GrayExecutionLog):
        if not log_item or not lock_resources:
            return
        for resource in lock_resources:
            if log_item.repository_id and resource.lock_key == f"gray_repo:{log_item.repository_id}:{log_item.target_branch or log_item.repository.branch}":
                resource.execution_log_id = log_item.id
                GrayExecutionLockService.bind_execution_log(resource, log_item.id)
                return
            if not log_item.repository_id and getattr(log_item, "gray_feature_id", None):
                resource.execution_log_id = log_item.id
                GrayExecutionLockService.bind_execution_log(resource, log_item.id)
                return

    @staticmethod
    def release_config_locks(configs: list | None):
        handles = []
        resources = []
        for config in configs or []:
            for handle in getattr(config, "_gray_lock_handles", []) or []:
                if handle not in handles:
                    handles.append(handle)
            for resource in getattr(config, "_gray_lock_resources", []) or []:
                if resource not in resources:
                    resources.append(resource)
        if handles:
            GrayExecutionLockService.release_handles(handles)
        elif resources:
            GrayExecutionLockService.release_resources(resources)

    @staticmethod
    def update_source_restore_status(config, restore_log):
        source_log_id = getattr(config, "_gray_execution_log_id", None)
        if not source_log_id:
            return
        try:
            source_log = GrayExecutionLog.objects.get(id=source_log_id)
        except GrayExecutionLog.DoesNotExist:
            return
        source_log.restore_commit_hash = restore_log.commit_hash
        if restore_log.status == GrayExecutionStatusEnum.SUCCESS.value:
            source_log.status = GrayExecutionStatusEnum.RESTORED.value
            source_log.error_message = None
        else:
            source_log.status = GrayExecutionStatusEnum.RESTORE_FAILED.value
            source_log.error_message = restore_log.error_message
        source_log.save(update_fields=["restore_commit_hash", "status", "error_message", "update_time"])

    @staticmethod
    def mark_source_restore_failed(config, error_message: str):
        source_log_id = getattr(config, "_gray_execution_log_id", None)
        if not source_log_id:
            return
        try:
            source_log = GrayExecutionLog.objects.get(id=source_log_id)
        except GrayExecutionLog.DoesNotExist:
            return
        source_log.status = GrayExecutionStatusEnum.RESTORE_FAILED.value
        source_log.error_message = error_message
        source_log.save(update_fields=["status", "error_message", "update_time"])

    @staticmethod
    def update_log_case_snapshot(log, case_snapshot: dict):
        persist_snapshot = {key: value for key, value in case_snapshot.items() if not key.startswith("_")}
        for key, value in persist_snapshot.items():
            setattr(log, key, value)
        log.save(update_fields=[*persist_snapshot.keys(), "update_time"])

    @staticmethod
    def variable_source(case_snapshot: dict) -> str | None:
        case_type = case_snapshot.get("case_type")
        if case_type == GrayCaseTypeEnum.API.value:
            return "api"
        if case_type == GrayCaseTypeEnum.UI.value:
            return "ui"
        return None

    @staticmethod
    def api_case_snapshot(
            api_case,
            test_suite_id: int | None = None,
            test_suite_detail_id: int | None = None,
            case_detailed=None,
            parameter=None,
            test_env: int | str | None = None,
    ) -> dict:
        return {
            "test_suite_id": test_suite_id,
            "test_suite_detail_id": test_suite_detail_id,
            "case_type": GrayCaseTypeEnum.API.value,
            "case_id": api_case.id,
            "case_name": api_case.name,
            "api_case_detailed_id": getattr(case_detailed, "id", None),
            "api_case_detailed_name": getattr(getattr(case_detailed, "api_info", None), "name", None),
            "api_case_detailed_parameter_id": getattr(parameter, "id", None),
            "api_case_detailed_parameter_name": getattr(parameter, "name", None),
            "_test_env": test_env,
        }
