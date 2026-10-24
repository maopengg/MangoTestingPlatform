# -*- coding: utf-8 -*-
import copy
import re

from src.apps.gray_config.enums import GrayActionEnum, GrayConfigTypeEnum
from src.apps.gray_config.exceptions import (
    GRAY_GRAY_NOT_FOUND,
    GRAY_EXECUTION_GRAY_UNSUPPORTED,
    GRAY_TYPE_CONFIG_GRAY_UNSUPPORTED,
    GrayConfigError,
)
from src.apps.gray_config.models import GrayFeature
from src.apps.gray_config.services.code_service import GrayCodeService
from src.apps.gray_config.services.lock import GrayExecutionLockService
from src.apps.gray_config.services.sql_service import GraySqlService
from src.apps.gray_config.services.target_resolver import GrayTargetValueResolver
from src.apps.gray_config.services.yaml_service import GrayYamlService


class GrayFeatureService:
    @classmethod
    def preview(
            cls,
            feature_id: int,
            target_value: str | None,
            action: str,
            variable_source: str | None = None,
            path_config: list[dict] | None = None,
            test_env: int | str | None = None,
    ) -> dict:
        cls.validate_action(action)
        feature = cls.resolve_runtime_feature(feature_id, test_env)
        cls.apply_path_config_override(feature, path_config)
        feature, resolved_target_value = cls.resolve_feature_variables(feature, target_value, variable_source, test_env)
        if feature.config_type == GrayConfigTypeEnum.YAML.value:
            result = GrayYamlService.preview_feature(feature, resolved_target_value, action)
        elif feature.config_type == GrayConfigTypeEnum.SQL.value:
            result = GraySqlService.preview_feature(feature, resolved_target_value, action)
        elif feature.config_type == GrayConfigTypeEnum.CODE.value:
            result = GrayCodeService.preview_feature(feature, resolved_target_value, action)
        else:
            raise GrayConfigError(GRAY_TYPE_CONFIG_GRAY_UNSUPPORTED)
        result.update({
            "target_expression": target_value or "",
            "resolved_target_value": resolved_target_value,
            "variable_source": variable_source or "",
        })
        return result

    @classmethod
    def execute(
            cls,
            feature_id: int,
            target_value: str | None,
            action: str,
            gray_config_id: int | None = None,
            variable_source: str | None = None,
            path_config: list[dict] | None = None,
            test_env: int | str | None = None,
            use_lock: bool = True,
    ):
        cls.validate_action(action)
        feature = cls.resolve_runtime_feature(feature_id, test_env)
        cls.apply_path_config_override(feature, path_config)
        feature, resolved_target_value = cls.resolve_feature_variables(feature, target_value, variable_source, test_env)
        if use_lock:
            with GrayExecutionLockService.locked(feature, resolved_target_value):
                return cls.execute_resolved_feature(feature, resolved_target_value, action, gray_config_id)
        return cls.execute_resolved_feature(feature, resolved_target_value, action, gray_config_id)

    @staticmethod
    def execute_resolved_feature(feature: GrayFeature, resolved_target_value: str, action: str,
                                 gray_config_id: int | None = None):
        if feature.config_type == GrayConfigTypeEnum.YAML.value:
            return GrayYamlService.execute_feature(feature, resolved_target_value, action, gray_config_id)
        if feature.config_type == GrayConfigTypeEnum.SQL.value:
            return GraySqlService.execute_feature(feature, resolved_target_value, action, gray_config_id)
        if feature.config_type == GrayConfigTypeEnum.CODE.value:
            return GrayCodeService.execute_feature(feature, resolved_target_value, action, gray_config_id)
        raise GrayConfigError(GRAY_TYPE_CONFIG_GRAY_UNSUPPORTED)

    @staticmethod
    def apply_path_config_override(feature: GrayFeature, path_config: list[dict] | None):
        if path_config is not None:
            feature.path_config = GrayFeatureService.normalize_path_config(path_config)

    @staticmethod
    def normalize_path_config(value) -> list[dict]:
        if not isinstance(value, list):
            return []
        result = []
        for item in value:
            if not isinstance(item, dict):
                continue
            path = str(item.get("path") or "").strip()
            if not path:
                continue
            result.append({
                "path": path,
                "value_type": str(item.get("value_type") or "number").strip(),
                "original_value": item.get("original_value"),
                "value": item.get("value"),
            })
        return result

    @classmethod
    def resolve_feature_variables(
            cls,
            feature: GrayFeature,
            target_value: str | None,
            variable_source: str | None,
            test_env: int | str | None,
    ) -> tuple[GrayFeature, str]:
        if feature.config_type != GrayConfigTypeEnum.YAML.value:
            return feature, GrayTargetValueResolver.resolve(feature, target_value, variable_source, test_env)
        resolved_feature = copy.copy(feature)
        resolved_feature.path_config = cls.resolve_path_config(feature, variable_source, test_env)
        return resolved_feature, ""

    @classmethod
    def resolve_path_config(
            cls,
            feature: GrayFeature,
            variable_source: str | None,
            test_env: int | str | None,
    ) -> list[dict]:
        result = []
        path_config = feature.path_config if isinstance(feature.path_config, list) else []
        for item in path_config:
            if not isinstance(item, dict):
                continue
            next_item = dict(item)
            for key in ("original_value", "value"):
                next_item[key] = cls.resolve_config_expression(feature, next_item.get(key), variable_source, test_env)
            result.append(next_item)
        return result

    @staticmethod
    def resolve_config_expression(
            feature: GrayFeature,
            value,
            variable_source: str | None,
            test_env: int | str | None,
    ):
        if not isinstance(value, str) or not re.search(r"\$\{\{[^}]+}}|\$\{[^}]+}", value):
            return value
        return GrayTargetValueResolver.resolve(feature, value, variable_source, test_env)

    @staticmethod
    def get_feature(feature_id: int) -> GrayFeature:
        try:
            return GrayFeature.objects.select_related(
                "project_product",
                "module",
                "yaml_file",
                "database",
            ).get(id=feature_id)
        except GrayFeature.DoesNotExist as exc:
            raise GrayConfigError(GRAY_GRAY_NOT_FOUND) from exc

    @classmethod
    def resolve_runtime_feature(cls, feature_id: int, test_env: int | str | None) -> GrayFeature:
        feature = cls.get_feature(feature_id)
        feature.runtime_environment = test_env
        if feature.config_type == GrayConfigTypeEnum.YAML.value:
            feature.yaml_file_binding = GrayYamlService.resolve_binding(feature.yaml_file, test_env)
            feature.yaml_file_binding_id = feature.yaml_file_binding.id
        return feature

    @staticmethod
    def validate_action(action: str):
        if action not in GrayActionEnum.obj():
            raise GrayConfigError(GRAY_EXECUTION_GRAY_UNSUPPORTED)
