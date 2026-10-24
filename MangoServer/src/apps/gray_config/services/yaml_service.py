# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from io import StringIO
from typing import Any

from django.utils import timezone
from mangotools.enums import StatusEnum

from src.apps.gray_config.enums import GrayActionEnum, GrayExecutionStatusEnum
from src.apps.gray_config.exceptions import (
    GRAY_FILE_GRAY_NOT_FOUND,
    GRAY_GRAY_NOT_FOUND,
    GRAY_FILE_BINDING_GRAY_INVALID,
    GRAY_FILE_DISABLED,
    GRAY_FILE_NOT_FOUND,
    GRAY_GRAY_INVALID,
    GRAY_PATH_GRAY_NOT_FOUND,
    GRAY_PATH_GRAY_REQUIRED,
    GRAY_PATH_INVALID,
    GRAY_GRAY_REQUIRED,
    GRAY_GRAY_INVALID_CODE_GRAY_INVALID,
    GRAY_YAML_NON_TARGET_KEY_CHANGED,
    GRAY_GRAY_REQUIRED_CODE_GRAY_REQUIRED,
    GRAY_PATH_NO_MATCH,
    GRAY_FILE_GRAY_NOT_FOUND_CODE_FILE_GRAY_NOT_FOUND,
    GRAY_FILE_REPOSITORY_CONFIG_BINDING_GRAY_INVALID,
    GrayConfigError,
)
from src.apps.gray_config.exceptions import GrayGitMergeError
from src.apps.gray_config.models import GrayExecutionLog, GrayFeature, GrayYamlFile, GrayYamlFileBinding
from src.apps.gray_config.services.git_service import GrayGitService
from src.apps.test_center.enums.environment import EnvironmentEnum


class GrayYamlService:
    @classmethod
    def read_file_content(cls, yaml_file_id: int, test_env: int | str | None = None,
                          binding_id: int | None = None) -> dict:
        try:
            yaml_file = GrayYamlFile.objects.get(id=yaml_file_id)
        except GrayYamlFile.DoesNotExist as exc:
            raise GrayConfigError(GRAY_FILE_GRAY_NOT_FOUND) from exc
        yaml_binding = cls.resolve_binding(yaml_file, test_env, binding_id)
        content = GrayGitService.read_file(yaml_binding.repository, yaml_binding.file_path)
        return {
            "yaml_file_id": yaml_file.id,
            "binding_id": yaml_binding.id,
            "repository_id": yaml_binding.repository_id,
            "file_path": yaml_binding.file_path,
            "content": content,
        }

    @classmethod
    def ensure_feature_key_exists(cls, yaml_file: GrayYamlFile, feature_key: str):
        feature_key = str(feature_key or "").strip()
        if not feature_key:
            raise GrayConfigError(GRAY_GRAY_REQUIRED)
        yaml_binding = cls.resolve_binding(yaml_file, None)
        document = cls.load_document(yaml_binding)
        try:
            cls.get_path(document, feature_key, feature_key)
        except GrayConfigError as exc:
            raise GrayConfigError(GRAY_FILE_GRAY_NOT_FOUND_CODE_FILE_GRAY_NOT_FOUND, value=(feature_key,)) from exc

    @classmethod
    def preview_feature(cls, feature: GrayFeature | int, target_value: str | None,
                        action: str = GrayActionEnum.ENABLE.value) -> dict:
        if not isinstance(feature, GrayFeature):
            try:
                feature = GrayFeature.objects.select_related("yaml_file").get(id=feature)
            except GrayFeature.DoesNotExist as exc:
                raise GrayConfigError(GRAY_GRAY_NOT_FOUND) from exc
        if not getattr(feature, "yaml_file_binding", None):
            feature.yaml_file_binding = cls.resolve_binding(feature.yaml_file, None)
        before_document = cls.load_document(feature.yaml_file_binding)
        after_document = cls.clone_document(before_document)
        before_snapshot = cls.extract_snapshot(before_document, feature)
        cls.apply_feature_document(after_document, feature, target_value, action)
        cls.validate_change_scope(before_document, after_document, feature)
        after_snapshot = cls.extract_snapshot(after_document, feature)
        before_text = cls.dump_snapshot_text(feature.feature_key, before_snapshot)
        after_text = cls.dump_snapshot_text(feature.feature_key, after_snapshot)
        return {
            "feature_id": feature.id,
            "feature_key": feature.feature_key,
            "target_value": target_value,
            "action": action,
            "before_snapshot": cls.json_safe_snapshot(before_snapshot),
            "after_snapshot": cls.json_safe_snapshot(after_snapshot),
            "before_text": before_text,
            "after_text": after_text,
            "file_path": feature.yaml_file_binding.file_path,
            "config_type": "yaml",
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
        yaml_file = feature.yaml_file
        yaml_binding = getattr(feature, "yaml_file_binding", None)
        if not yaml_file or not yaml_binding:
            raise GrayConfigError(GRAY_FILE_BINDING_GRAY_INVALID)
        log = GrayExecutionLog.objects.create(
            gray_config_id=gray_config_id,
            gray_feature=feature,
            repository=yaml_binding.repository,
            config_type=feature.config_type,
            yaml_file=yaml_file,
            yaml_file_binding=yaml_binding,
            feature_key=feature.feature_key,
            target_value=target_value,
            action=action,
            status=GrayExecutionStatusEnum.WAITING.value,
            started_at=timezone.now(),
            **(case_snapshot or {}),
        )
        try:
            document = cls.load_document(yaml_binding)
            log.before_snapshot = cls.extract_snapshot(document, feature)
            before_document = cls.clone_document(document)
            cls.apply_feature_document(document, feature, target_value, action)
            cls.validate_change_scope(before_document, document, feature)
            log.after_snapshot = cls.extract_snapshot(document, feature)
            source_branch = GrayGitService.gray_work_branch(feature.feature_key, action)
            content = cls.dump_document_text(document)
            info = GrayGitService.commit_content_and_merge_request(
                yaml_binding.repository,
                file_path=yaml_binding.file_path,
                content=content,
                message=f"test-platform gray {action} {feature.feature_key}",
                feature_key=feature.feature_key,
                action=action,
                source_branch=source_branch,
            )
            log.commit_hash = info.get("latest_commit") or info.get("commit_hash") or info.get("short_commit")
            cls.fill_merge_request_log(log, info)
            log.status = GrayExecutionStatusEnum.SUCCESS.value
        except GrayGitMergeError as error:
            info = error.info or {}
            log.commit_hash = info.get("latest_commit") or info.get("commit_hash") or info.get("short_commit")
            cls.fill_merge_request_log(log, info)
            log.status = GrayExecutionStatusEnum.FAILED.value
            log.error_message = str(error)
        except Exception as error:
            log.status = GrayExecutionStatusEnum.FAILED.value
            log.error_message = str(error)
            GrayGitService.reset_to_target_branch(yaml_binding.repository)
        finally:
            log.finished_at = timezone.now()
            log.save()
        return log

    @staticmethod
    def fill_merge_request_log(log: GrayExecutionLog, info: dict):
        merge_request = info.get("merge_request") or {}
        log.source_branch = info.get("source_branch")
        log.target_branch = info.get("target_branch")
        log.merge_request_id = str(merge_request.get("id") or "") or None
        log.merge_request_iid = str(merge_request.get("iid") or "") or None
        log.merge_request_url = merge_request.get("web_url")
        log.merge_request_state = merge_request.get("state")

    @classmethod
    def load_document(cls, yaml_binding: GrayYamlFileBinding):
        content = cls.remote_file_content(yaml_binding)
        yaml = cls.yaml()
        return yaml.load(StringIO(content)) or {}

    @classmethod
    def dump_document_text(cls, document) -> str:
        stream = StringIO()
        yaml = cls.yaml()
        yaml.dump(document, stream)
        return stream.getvalue()

    @classmethod
    def remote_file_content(cls, yaml_binding: GrayYamlFileBinding) -> str:
        if yaml_binding.status != StatusEnum.SUCCESS.value or yaml_binding.yaml_file.status != StatusEnum.SUCCESS.value:
            raise GrayConfigError(GRAY_FILE_DISABLED)
        try:
            return GrayGitService.read_file(yaml_binding.repository, yaml_binding.file_path)
        except Exception as exc:
            raise GrayConfigError(GRAY_FILE_NOT_FOUND, value=(yaml_binding.file_path,)) from exc

    @classmethod
    def resolve_binding(
            cls,
            yaml_file: GrayYamlFile,
            test_env: int | str | None = None,
            binding_id: int | None = None,
    ) -> GrayYamlFileBinding:
        if yaml_file is None:
            raise GrayConfigError(GRAY_FILE_BINDING_GRAY_INVALID)
        if binding_id:
            try:
                return GrayYamlFileBinding.objects.select_related("yaml_file", "repository").get(
                    id=binding_id,
                    yaml_file=yaml_file,
                )
            except GrayYamlFileBinding.DoesNotExist as exc:
                raise GrayConfigError(GRAY_FILE_REPOSITORY_CONFIG_BINDING_GRAY_INVALID, value=("指定绑定",)) from exc
        env_value = cls.normalize_env(test_env)
        queryset = GrayYamlFileBinding.objects.select_related("yaml_file", "repository").filter(
            yaml_file=yaml_file,
            status=StatusEnum.SUCCESS.value,
            repository__status=StatusEnum.SUCCESS.value,
        )
        if env_value is None:
            binding = queryset.filter(repository__test_env__isnull=True).first() or queryset.first()
            if binding:
                return binding
            raise GrayConfigError(GRAY_FILE_REPOSITORY_CONFIG_BINDING_GRAY_INVALID, value=("任意环境",))
        if env_value is not None:
            binding = queryset.filter(repository__test_env=env_value).first()
            if binding:
                return binding
        binding = queryset.filter(repository__test_env__isnull=True).first()
        if binding:
            return binding
        raise GrayConfigError(GRAY_FILE_REPOSITORY_CONFIG_BINDING_GRAY_INVALID, value=(cls.env_label(env_value),))

    @staticmethod
    def normalize_env(test_env: int | str | None) -> int | None:
        if test_env in (None, ""):
            return None
        try:
            return int(test_env)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def env_label(test_env: int | None) -> str:
        if test_env is None:
            return "环境通用"
        return EnvironmentEnum.get_value(test_env) or f"环境{test_env}"

    @classmethod
    def apply_feature_document(cls, document, feature: GrayFeature, target_value: str | None, action: str):
        current = cls.get_path(document, feature.feature_key, feature.feature_key)
        if not isinstance(current, dict):
            raise GrayConfigError(GRAY_GRAY_INVALID, value=(feature.feature_key,))
        cls.apply_path_config(current, feature, target_value, action)

    @classmethod
    def apply_path_config(cls, document, feature: GrayFeature, target_value: str | None, action: str):
        path_config = feature.path_config if isinstance(feature.path_config, list) else []
        for item in path_config:
            if not isinstance(item, dict):
                continue
            path = str(item.get("path") or "").strip()
            if not path:
                continue
            config_value = cls.resolve_config_value(item.get("value"), target_value, action, item.get("value_type"))
            original_value = cls.resolve_original_value(item.get("original_value"), target_value, action)
            if action == GrayActionEnum.RESTORE.value:
                config_value, original_value = original_value, config_value
            cls.apply_path_item(
                document,
                path,
                config_value,
                original_value,
            )

    @classmethod
    def apply_path_item(cls, document, path: str, value, original_value):
        current = cls.get_path(document, path, default=None)
        if isinstance(current, list):
            cls.set_path(document, path, cls.apply_list_value(path, current, original_value, value))
            return
        cls.set_path_if_original_matched(document, path, current, value, original_value)

    @classmethod
    def resolve_config_value(cls, value, target_value: str | None, action: str, value_type: str | None = None):
        if isinstance(value, str):
            value = value.strip()
            if value in {"${{target_value}}", "${target_value}"}:
                return cls.cast_config_value(target_value or "", value_type)
            if value == "${{action}}":
                return cls.cast_config_value(action, value_type)
        return cls.cast_config_value(value, value_type)

    @staticmethod
    def resolve_original_value(value, target_value: str | None, action: str):
        if isinstance(value, str):
            value = value.strip()
            if value in {"${{target_value}}", "${target_value}"}:
                return target_value or ""
            if value == "${{action}}":
                return action
        return value

    @classmethod
    def cast_config_value(cls, value, value_type: str | None = None):
        value_type = str(value_type or "number").strip() or "number"
        if value_type == "auto":
            value_type = "number"
        if value is None or value == "":
            return value
        if value_type == "string":
            return str(value)
        if value_type == "number":
            return cls.cast_number(value)
        if value_type == "boolean":
            return cls.cast_boolean(value)
        if value_type == "json":
            return cls.cast_json(value)
        return cls.cast_number(value)

    @staticmethod
    def cast_number(value):
        try:
            number = Decimal(str(value))
        except InvalidOperation:
            return value
        if number == number.to_integral_value():
            return int(number)
        return float(number)

    @staticmethod
    def cast_boolean(value):
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"true", "1", "yes", "y", "on"}

    @staticmethod
    def cast_json(value):
        if not isinstance(value, str):
            return value
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    @staticmethod
    def has_original_value(value) -> bool:
        return value not in (None, "")

    @staticmethod
    def value_matches(current, expected) -> bool:
        if isinstance(current, bool) and isinstance(expected, str):
            return str(current).lower() == expected.strip().lower()
        if current is None and isinstance(expected, str):
            return expected.strip().lower() == "null"
        return str(current) == str(expected)

    @classmethod
    def set_path_if_original_matched(cls, document, path: str, current, value, original_value):
        if not cls.has_original_value(original_value):
            cls.set_path(document, path, value)
            return
        if cls.value_matches(current, original_value):
            cls.set_path(document, path, value)
            return
        raise GrayConfigError(GRAY_PATH_NO_MATCH, value=(path, current, original_value))

    @classmethod
    def replace_list_value(cls, path: str, items: list, original_value, new_value):
        result = []
        matched = False
        for item in items:
            if cls.value_matches(item, original_value):
                matched = True
                if new_value not in (None, "") and str(new_value) not in [str(value) for value in result]:
                    result.append(new_value)
            else:
                result.append(item)
        if not matched:
            raise GrayConfigError(GRAY_PATH_NO_MATCH, value=(path, items, original_value))
        return result

    @classmethod
    def apply_list_value(cls, path: str, items: list, original_value, new_value):
        if cls.has_original_value(original_value):
            return cls.replace_list_value(path, items, original_value, new_value)
        result = list(items)
        if new_value not in (None, "") and str(new_value) not in [str(value) for value in result]:
            result.append(new_value)
        return result

    @classmethod
    def extract_snapshot(cls, document, feature: GrayFeature) -> Any:
        try:
            return cls.get_path(document, feature.feature_key, feature.feature_key)
        except GrayConfigError:
            return None

    @classmethod
    def dump_snapshot_text(cls, feature_key: str, snapshot: Any) -> str:
        stream = StringIO()
        yaml = cls.yaml()
        yaml.dump({feature_key: snapshot}, stream)
        return stream.getvalue()

    @classmethod
    def json_safe_snapshot(cls, value):
        if isinstance(value, int) and abs(value) > 9007199254740991:
            return str(value)
        if isinstance(value, list):
            return [cls.json_safe_snapshot(item) for item in value]
        if isinstance(value, dict):
            return {key: cls.json_safe_snapshot(item) for key, item in value.items()}
        return value

    @staticmethod
    def path_parts(path: str) -> list[str]:
        return [item for item in str(path or "").split(".") if item]

    @classmethod
    def get_path(cls, document, path: str, label: str | None = None, default=None):
        current = document
        for part in cls.path_parts(path):
            if not isinstance(current, dict) or part not in current:
                if default is not None:
                    return default
                raise GrayConfigError(GRAY_PATH_GRAY_NOT_FOUND, value=(label or path,))
            current = current[part]
        return current

    @classmethod
    def set_path(cls, document, path: str, value):
        current = document
        parts = cls.path_parts(path)
        if not parts:
            raise GrayConfigError(GRAY_PATH_GRAY_REQUIRED)
        for part in parts[:-1]:
            if part not in current or current[part] is None:
                current[part] = {}
            if not isinstance(current[part], dict):
                raise GrayConfigError(GRAY_PATH_INVALID, value=(path,))
            current = current[part]
        current[parts[-1]] = value

    @classmethod
    def validate_change_scope(cls, before_document, after_document, feature: GrayFeature):
        root_parts = cls.path_parts(feature.feature_key)
        if not root_parts:
            raise GrayConfigError(GRAY_GRAY_REQUIRED)
        before_compare = cls.clone_document(before_document)
        after_compare = cls.clone_document(after_document)
        before_keys = set(before_compare.keys()) if isinstance(before_compare, dict) else set()
        after_keys = set(after_compare.keys()) if isinstance(after_compare, dict) else set()
        if before_keys != after_keys:
            raise GrayConfigError(GRAY_GRAY_INVALID_CODE_GRAY_INVALID)
        marker = {"__mango_gray_target__": feature.feature_key}
        cls.set_path(before_compare, feature.feature_key, marker)
        cls.set_path(after_compare, feature.feature_key, marker)
        if before_compare != after_compare:
            raise GrayConfigError(GRAY_YAML_NON_TARGET_KEY_CHANGED, value=(feature.feature_key,))

    @staticmethod
    def clone_document(document):
        yaml = GrayYamlService.yaml()
        stream = StringIO()
        yaml.dump(document, stream)
        stream.seek(0)
        return yaml.load(stream) or {}

    @staticmethod
    def yaml() -> YAML:
        try:
            from ruamel.yaml import YAML
        except ModuleNotFoundError as exc:
            raise GrayConfigError(GRAY_GRAY_REQUIRED_CODE_GRAY_REQUIRED) from exc
        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.indent(mapping=2, sequence=4, offset=2)
        return yaml
