import copy
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from django.db import models

from src.apps.auto_api.enums import ApiConfigObjectTypeEnum
from src.apps.auto_api.models import (
    ApiCase,
    ApiCaseDetailed,
    ApiCaseDetailedParameter,
    ApiInfo,
)


@dataclass(frozen=True)
class ApiConfigSnapshot:
    object_type: str
    object_id: int
    snapshot: dict | None


@dataclass(frozen=True)
class ApiConfigSnapshotPathIndex:
    total_occurrences: dict[str, int]

    def contains(self, path: str) -> bool:
        return self.total_occurrences.get(path, 0) > 0

    def occurs_once(self, path: str) -> bool:
        return self.total_occurrences.get(path, 0) == 1


@dataclass(frozen=True)
class JsonLikeToken:
    kind: str
    value: str
    raw: str
    reliable: bool


@dataclass
class JsonLikeContext:
    kind: str
    state: str
    property_name: str = ''


class ApiConfigSnapshotService:
    """生成接口/用例配置快照，专门用于版本追溯。"""

    EXCLUDED_FIELDS = {'create_time', 'update_time'}
    SENSITIVE_KEYS = frozenset({
        'authorization',
        'token',
        'password',
        'secret',
        'cookie',
        'access_key',
        'refresh_token',
        'app_secret',
        'cache_data',
        'api_key',
    })
    SENSITIVE_SUFFIX_PATTERN = re.compile(
        r'_(?:authorization|token|password|secret|cookie|api_key|access_key)$'
    )
    NON_CREDENTIAL_TOKEN_KEYS = frozenset({
        'page_token',
        'next_page_token',
    })
    RUNTIME_SECRET_REFERENCE_PATTERN = re.compile(
        r'\$\{\{[^{}]+\}\}|\$\{secret_required:[^{}]+\}'
    )
    RUNTIME_SECRET_REFERENCE_PREFIXES = frozenset({'', 'bearer', 'basic', 'token'})

    @classmethod
    def capture_for_instance(cls, instance) -> ApiConfigSnapshot:
        target = cls.resolve_target(instance)
        if target is None:
            return ApiConfigSnapshot('', 0, None)
        object_type, object_id = target
        return ApiConfigSnapshot(object_type, object_id, cls.capture_target(object_type, object_id))

    @classmethod
    def capture_target(cls, object_type: str, object_id: int) -> dict | None:
        if object_type == ApiConfigObjectTypeEnum.API_INFO:
            api_info = ApiInfo.objects.filter(id=object_id).first()
            if not api_info:
                return None
            return cls.serialize_model(api_info)
        if object_type == ApiConfigObjectTypeEnum.API_CASE:
            return cls.capture_api_case(object_id)
        return None

    @classmethod
    def capture_api_case(cls, case_id: int) -> dict | None:
        api_case = ApiCase.objects.filter(id=case_id).first()
        if not api_case:
            return None
        data = cls.serialize_model(api_case)
        data['steps'] = []
        steps = ApiCaseDetailed.objects.filter(case_id=case_id).order_by('case_sort', 'id')
        for step in steps:
            step_data = cls.serialize_model(step)
            parameters = ApiCaseDetailedParameter.objects.filter(case_detailed_id=step.id).order_by('id')
            step_data['parameters'] = [cls.serialize_model(parameter) for parameter in parameters]
            data['steps'].append(step_data)
        data['data_factory_configs'] = cls.serialize_data_factory_configs(case_id)
        data['gray_configs'] = cls.serialize_gray_configs(case_id)
        return data

    @classmethod
    def resolve_target(cls, instance) -> tuple[str, int] | None:
        if isinstance(instance, ApiInfo):
            return ApiConfigObjectTypeEnum.API_INFO, instance.id
        if isinstance(instance, ApiCase):
            return ApiConfigObjectTypeEnum.API_CASE, instance.id
        if isinstance(instance, ApiCaseDetailed):
            return ApiConfigObjectTypeEnum.API_CASE, instance.case_id
        if isinstance(instance, ApiCaseDetailedParameter):
            case_id = ApiCaseDetailed.objects.filter(id=instance.case_detailed_id).values_list('case_id',
                                                                                               flat=True).first()
            if case_id:
                return ApiConfigObjectTypeEnum.API_CASE, case_id
        data_factory_target = cls.resolve_data_factory_target(instance)
        if data_factory_target:
            return data_factory_target
        gray_target = cls.resolve_gray_target(instance)
        if gray_target:
            return gray_target
        return None

    @classmethod
    def resolve_data_factory_target(cls, instance) -> tuple[str, int] | None:
        try:
            from src.apps.data_factory.models import DataFactoryCaseConfig
            from src.apps.data_factory.enums import DataFactoryCaseSourceTypeEnum
        except ImportError:
            return None
        if not isinstance(instance, DataFactoryCaseConfig):
            return None
        if instance.source_type == DataFactoryCaseSourceTypeEnum.API_CASE.value:
            return ApiConfigObjectTypeEnum.API_CASE, instance.source_id
        if instance.source_type == DataFactoryCaseSourceTypeEnum.API_CASE_PARAMETER.value:
            case_id = ApiCaseDetailedParameter.objects.filter(
                id=instance.source_id,
            ).values_list('case_detailed__case_id', flat=True).first()
            if case_id:
                return ApiConfigObjectTypeEnum.API_CASE, case_id
        return None

    @classmethod
    def resolve_gray_target(cls, instance) -> tuple[str, int] | None:
        try:
            from src.apps.gray_config.enums import GrayCaseTypeEnum
            from src.apps.gray_config.models import AutomationCaseGrayConfig
        except ImportError:
            return None
        if (
                not isinstance(instance, AutomationCaseGrayConfig) or
                instance.case_type != GrayCaseTypeEnum.API.value
        ):
            return None
        if instance.api_case_id:
            return ApiConfigObjectTypeEnum.API_CASE, instance.api_case_id
        if instance.api_case_detailed_id:
            case_id = ApiCaseDetailed.objects.filter(
                id=instance.api_case_detailed_id,
            ).values_list('case_id', flat=True).first()
            if case_id:
                return ApiConfigObjectTypeEnum.API_CASE, case_id
        if instance.api_case_detailed_parameter_id:
            case_id = ApiCaseDetailedParameter.objects.filter(
                id=instance.api_case_detailed_parameter_id,
            ).values_list('case_detailed__case_id', flat=True).first()
            if case_id:
                return ApiConfigObjectTypeEnum.API_CASE, case_id
        return None

    @classmethod
    def serialize_model(cls, instance) -> dict:
        data = {}
        for field in instance._meta.fields:
            if field.name in cls.EXCLUDED_FIELDS:
                continue
            if isinstance(field, models.ForeignKey):
                value = getattr(instance, field.attname)
            else:
                value = getattr(instance, field.name)
            data[field.name] = cls.to_jsonable(value)
        return data

    @classmethod
    def serialize_data_factory_configs(cls, case_id: int) -> list[dict]:
        try:
            from src.apps.data_factory.models import DataFactoryCaseConfig
            from src.apps.data_factory.enums import DataFactoryCaseSourceTypeEnum
        except ImportError:
            return []
        querysets = [
            DataFactoryCaseConfig.objects.filter(
                source_type=DataFactoryCaseSourceTypeEnum.API_CASE.value,
                source_id=case_id,
            ),
            DataFactoryCaseConfig.objects.filter(
                source_type=DataFactoryCaseSourceTypeEnum.API_CASE_PARAMETER.value,
                source_id__in=ApiCaseDetailedParameter.objects.filter(
                    case_detailed__case_id=case_id,
                ).values_list('id', flat=True),
            ),
        ]
        configs = []
        for queryset in querysets:
            for config in queryset.order_by('source_type', 'source_id', 'sort', 'id'):
                configs.append(cls.serialize_model(config))
        return configs

    @classmethod
    def serialize_gray_configs(cls, case_id: int) -> list[dict]:
        try:
            from src.apps.gray_config.enums import GrayCaseTypeEnum
            from src.apps.gray_config.models import AutomationCaseGrayConfig
        except ImportError:
            return []
        queryset = AutomationCaseGrayConfig.objects.filter(
            case_type=GrayCaseTypeEnum.API.value,
        ).filter(
            models.Q(api_case_id=case_id) |
            models.Q(api_case_detailed__case_id=case_id) |
            models.Q(api_case_detailed_parameter__case_detailed__case_id=case_id)
        ).order_by('scope', 'sort', 'id')
        return [cls.serialize_model(config) for config in queryset]

    @classmethod
    def sanitize_value(cls, value: Any, key: str = '') -> Any:
        if cls.is_sensitive_key(key) and not cls.is_runtime_secret_reference(value):
            return '***'
        if isinstance(value, dict):
            has_sensitive_semantic_key = cls.has_sensitive_semantic_key(value)
            return {
                item_key: (
                    '***'
                    if item_key == 'value' and has_sensitive_semantic_key
                    else cls.sanitize_value(item_value, str(item_key))
                )
                for item_key, item_value in value.items()
            }
        if isinstance(value, list):
            return [cls.sanitize_value(item, key) for item in value]
        if isinstance(value, str):
            is_json_container, parsed_value = cls.parse_json_container(value)
            if is_json_container:
                sanitized_value = cls.sanitize_value(parsed_value)
                return json.dumps(sanitized_value, ensure_ascii=False)
            if cls.has_sensitive_json_hint(value):
                return '***'
        return value

    @classmethod
    def is_runtime_secret_reference(cls, value: Any) -> bool:
        if not isinstance(value, str):
            return False
        if not cls.RUNTIME_SECRET_REFERENCE_PATTERN.search(value):
            return False
        remainder = cls.RUNTIME_SECRET_REFERENCE_PATTERN.sub('', value).strip().lower()
        return remainder in cls.RUNTIME_SECRET_REFERENCE_PREFIXES

    @classmethod
    def parse_json_container(cls, value: str) -> tuple[bool, Any]:
        stripped_value = cls.strip_json_like_prefix(value)
        if not stripped_value.startswith(('{', '[')):
            return False, None
        try:
            parsed_value = json.loads(value, parse_constant=cls.reject_non_standard_json_constant)
        except (json.JSONDecodeError, TypeError, ValueError):
            return False, None
        return isinstance(parsed_value, (dict, list)), parsed_value

    @staticmethod
    def reject_non_standard_json_constant(value: str):
        raise ValueError(f'non-standard JSON constant: {value}')

    @classmethod
    def has_sensitive_json_hint(cls, value: str) -> bool:
        stripped_value = cls.strip_json_like_prefix(value)
        if not stripped_value.startswith(('{', '[')):
            return False
        contexts: list[JsonLikeContext] = []
        for token in cls.tokenize_json_like(value):
            if token.kind == 'punctuation':
                if token.value in ('{', '['):
                    cls.consume_json_like_container_value(contexts)
                    contexts.append(JsonLikeContext(
                        kind='object' if token.value == '{' else 'array',
                        state='key' if token.value == '{' else 'value',
                    ))
                elif token.value in ('}', ']'):
                    if contexts:
                        contexts.pop()
                elif token.value == ':' and contexts:
                    context = contexts[-1]
                    if context.kind == 'object' and context.state == 'colon':
                        if cls.is_sensitive_key(context.property_name):
                            return True
                        context.state = 'value'
                elif token.value == ',' and contexts:
                    context = contexts[-1]
                    context.state = 'key' if context.kind == 'object' else 'value'
                    context.property_name = ''
                continue

            if not contexts:
                continue
            context = contexts[-1]
            if context.kind == 'array':
                if context.state == 'value':
                    context.state = 'comma'
                continue
            if context.state == 'key':
                embedded_key = token.value.split(':', 1)[0].strip()
                if ':' in token.value and cls.is_sensitive_key(embedded_key):
                    return True
                context.property_name = token.value
                context.state = 'colon'
                continue
            if context.state == 'value':
                if (
                        context.property_name in ('key', 'name') and
                        (not token.reliable or cls.is_sensitive_key(token.value))
                ):
                    return True
                context.state = 'comma'
        return False

    @staticmethod
    def strip_json_like_prefix(value: str) -> str:
        position = 0
        while position < len(value) and (value[position].isspace() or value[position] == '\ufeff'):
            position += 1
        return value[position:]

    @classmethod
    def contains_sensitive_structure(cls, value: Any) -> bool:
        if isinstance(value, dict):
            semantic_sensitive = cls.has_sensitive_semantic_key(value)
            return any(
                cls.is_sensitive_key(str(key)) or
                (key == 'value' and semantic_sensitive) or
                cls.contains_sensitive_structure(item)
                for key, item in value.items()
            )
        if isinstance(value, list):
            return any(cls.contains_sensitive_structure(item) for item in value)
        if isinstance(value, str):
            is_json_container, parsed_value = cls.parse_json_container(value)
            if is_json_container:
                return cls.contains_sensitive_structure(parsed_value)
            return cls.has_sensitive_json_hint(value)
        return False

    @classmethod
    def tokenize_json_like(cls, value: str) -> list[JsonLikeToken]:
        tokens = []
        position = 0
        while position < len(value):
            if value[position].isspace() or value[position] == '\ufeff':
                position += 1
                continue
            if value.startswith('/*', position):
                comment_end = value.find('*/', position + 2)
                position = len(value) if comment_end < 0 else comment_end + 2
                continue
            if value.startswith('//', position):
                line_end = value.find('\n', position + 2)
                position = len(value) if line_end < 0 else line_end
                continue
            if value[position] in '{}[]:,':
                tokens.append(JsonLikeToken('punctuation', value[position], value[position], True))
                position += 1
                continue
            quote = value[position]
            if quote not in ('"', "'"):
                start = position
                while (
                        position < len(value) and
                        not value[position].isspace() and
                        value[position] != '\ufeff' and
                        value[position] not in '{}[]:,\"\'' and
                        not value.startswith('/*', position) and
                        not value.startswith('//', position)
                ):
                    position += 1
                if position == start:
                    position += 1
                    continue
                raw = value[start:position]
                tokens.append(JsonLikeToken('bare', raw, raw, True))
                continue
            start = position
            position += 1
            is_closed = False
            while position < len(value):
                if value[position] == '\\':
                    position = min(position + 2, len(value))
                    continue
                if value[position] == quote:
                    position += 1
                    is_closed = True
                    break
                position += 1
            raw = value[start:position]
            decoded_value, reliable = cls.decode_json_like_token(raw, is_closed)
            tokens.append(JsonLikeToken(
                'quoted',
                decoded_value,
                raw,
                reliable,
            ))
        return tokens

    @staticmethod
    def consume_json_like_container_value(contexts: list[JsonLikeContext]):
        if contexts and contexts[-1].state == 'value':
            contexts[-1].state = 'comma'

    @staticmethod
    def decode_json_like_token(value: str, is_closed: bool) -> tuple[str, bool]:
        content = value[1:-1] if is_closed else value[1:]
        if value.startswith('"'):
            encoded_value = value if is_closed else f'{value}"'
        else:
            encoded_content = []
            position = 0
            while position < len(content):
                if content[position] == '\\' and position + 1 < len(content):
                    if content[position + 1] == "'":
                        encoded_content.append("'")
                    else:
                        encoded_content.extend((content[position], content[position + 1]))
                    position += 2
                    continue
                encoded_content.append('\\"' if content[position] == '"' else content[position])
                position += 1
            encoded_value = f'"{"".join(encoded_content)}"'
        try:
            decoded_value = json.loads(encoded_value)
            return decoded_value, isinstance(decoded_value, str)
        except (json.JSONDecodeError, TypeError):
            return content, False

    @classmethod
    def is_sensitive_key(cls, key: str) -> bool:
        normalized = cls.normalize_sensitive_key(str(key))
        if normalized in cls.NON_CREDENTIAL_TOKEN_KEYS:
            return False
        return normalized in cls.SENSITIVE_KEYS or bool(cls.SENSITIVE_SUFFIX_PATTERN.search(normalized))

    @staticmethod
    def normalize_sensitive_key(value: str) -> str:
        normalized = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', value)
        normalized = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', normalized)
        normalized = re.sub(r'[^A-Za-z0-9]+', '_', normalized)
        normalized = re.sub(r'_+', '_', normalized)
        return normalized.lower().strip('_')

    @classmethod
    def has_sensitive_semantic_key(cls, value: Any) -> bool:
        if not isinstance(value, dict):
            return False
        return any(
            isinstance(value.get(field_name), str) and cls.is_sensitive_key(value[field_name])
            for field_name in ('key', 'name')
        )

    @classmethod
    def to_jsonable(cls, value: Any) -> Any:
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, Decimal):
            return str(value)
        try:
            return json.loads(json.dumps(value, ensure_ascii=False, default=str))
        except TypeError:
            return str(value)


class ApiConfigDiffService:
    """旧通用版本记录已废弃；仅保留脱敏/差异工具给历史 UI 代码复用。"""

    _MISSING = object()

    @classmethod
    def record_instance_change(
            cls,
            instance,
            action: str,
            before_snapshot: dict | None = None,
            after_snapshot: dict | None = None,
            operator_id: int | None = None,
            source: str = 'system',
            summary: str | None = None,
            change_group_id: str | None = None,
    ) -> None:
        return None

    @classmethod
    def record_change(
            cls,
            object_type: str,
            object_id: int,
            action: str,
            before_snapshot: dict | None,
            after_snapshot: dict | None,
            operator_id: int | None = None,
            source: str = 'system',
            summary: str | None = None,
            change_group_id: str | None = None,
    ) -> None:
        return None

    @classmethod
    def sanitize_audit_data(
            cls,
            before_snapshot: Any,
            after_snapshot: Any,
            candidate_diff: list[dict] | None = None,
    ) -> tuple[Any, Any, list[dict]]:
        safe_before, safe_after, safe_diff = cls.sanitize_audit_data_for_storage(
            before_snapshot,
            after_snapshot,
            candidate_diff,
        )
        return (
            safe_before,
            safe_after,
            [
                {key: value for key, value in item.items() if key != 'masked'}
                for item in safe_diff
            ],
        )

    @classmethod
    def sanitize_audit_data_for_storage(
            cls,
            before_snapshot: Any,
            after_snapshot: Any,
            candidate_diff: list[dict] | None = None,
    ) -> tuple[Any, Any, list[dict]]:
        raw_diff = cls.diff_snapshots_with_segments(before_snapshot, after_snapshot)
        safe_before_snapshot, safe_after_snapshot, _ = cls.sanitize_snapshot_pair(
            before_snapshot,
            after_snapshot,
        )
        safe_diff = [
            cls.sanitize_diff_item(item, before_snapshot, after_snapshot)
            for item in raw_diff
        ]
        if candidate_diff:
            safe_diff = cls.merge_redacted_candidate_diff(
                safe_diff,
                before_snapshot,
                after_snapshot,
                candidate_diff,
            )
        return safe_before_snapshot, safe_after_snapshot, safe_diff

    @classmethod
    def sanitize_snapshot_pair(cls, before: Any, after: Any) -> tuple[Any, Any, bool]:
        before_exists = before is not cls._MISSING
        after_exists = after is not cls._MISSING
        if isinstance(before, dict) and isinstance(after, dict):
            before_semantic_sensitive = ApiConfigSnapshotService.has_sensitive_semantic_key(before)
            after_semantic_sensitive = ApiConfigSnapshotService.has_sensitive_semantic_key(after)
            sanitized_by_key = {}
            for key in set(before) | set(after):
                before_value = before.get(key, cls._MISSING)
                after_value = after.get(key, cls._MISSING)
                is_sensitive_boundary = (
                        ApiConfigSnapshotService.is_sensitive_key(str(key)) or
                        (
                                key == 'value' and
                                (before_semantic_sensitive or after_semantic_sensitive)
                        )
                )
                if is_sensitive_boundary:
                    sanitized_by_key[key] = (
                        '***' if before_value is not cls._MISSING else cls._MISSING,
                        '***' if after_value is not cls._MISSING else cls._MISSING,
                        True,
                    )
                    continue
                sanitized_by_key[key] = cls.sanitize_snapshot_pair(before_value, after_value)
            return (
                {key: sanitized_by_key[key][0] for key in before},
                {key: sanitized_by_key[key][1] for key in after},
                any(item[2] for item in sanitized_by_key.values()),
            )

        if isinstance(before, list) and isinstance(after, list):
            sanitized_items = [
                cls.sanitize_snapshot_pair(
                    before[index] if index < len(before) else cls._MISSING,
                    after[index] if index < len(after) else cls._MISSING,
                )
                for index in range(max(len(before), len(after)))
            ]
            return (
                [sanitized_items[index][0] for index in range(len(before))],
                [sanitized_items[index][1] for index in range(len(after))],
                any(item[2] for item in sanitized_items),
            )

        if isinstance(before, str) and isinstance(after, str):
            before_is_json, before_json = ApiConfigSnapshotService.parse_json_container(before)
            after_is_json, after_json = ApiConfigSnapshotService.parse_json_container(after)
            if before_is_json and after_is_json:
                safe_before_json, safe_after_json, masked = cls.sanitize_snapshot_pair(
                    before_json,
                    after_json,
                )
                return (
                    json.dumps(safe_before_json, ensure_ascii=False),
                    json.dumps(safe_after_json, ensure_ascii=False),
                    masked,
                )

        before_sensitive = (
                before_exists and ApiConfigSnapshotService.contains_sensitive_structure(before)
        )
        after_sensitive = (
                after_exists and ApiConfigSnapshotService.contains_sensitive_structure(after)
        )
        if (
                before_exists and
                after_exists and
                (before_sensitive or after_sensitive)
        ):
            return '***', '***', True

        return (
            cls._MISSING
            if not before_exists
            else ApiConfigSnapshotService.sanitize_value(copy.deepcopy(before)),
            cls._MISSING
            if not after_exists
            else ApiConfigSnapshotService.sanitize_value(copy.deepcopy(after)),
            before_sensitive or after_sensitive,
        )

    @classmethod
    def merge_redacted_candidate_diff(
            cls,
            safe_diff: list[dict],
            before_snapshot: Any,
            after_snapshot: Any,
            candidate_diff: list[dict],
    ) -> list[dict]:
        merged_diff = list(safe_diff)
        existing_paths = {item.get('path') for item in merged_diff}
        before_index = cls.build_snapshot_path_index(before_snapshot)
        after_index = cls.build_snapshot_path_index(after_snapshot)
        for candidate in candidate_diff:
            if not isinstance(candidate, dict) or candidate.get('masked') is not True:
                continue
            path = candidate.get('path')
            if not isinstance(path, str) or not path or path in existing_paths:
                continue
            before_exists = before_index.contains(path)
            after_exists = after_index.contains(path)
            if not before_exists and not after_exists:
                continue
            if (
                    (before_exists and not before_index.occurs_once(path)) or
                    (after_exists and not after_index.occurs_once(path))
            ):
                continue
            diff_type = 'changed'
            if not before_exists:
                diff_type = 'added'
            elif not after_exists:
                diff_type = 'removed'
            merged_diff.append({
                'path': path,
                'type': diff_type,
                'before': '***' if before_exists else None,
                'after': '***' if after_exists else None,
                'masked': True,
            })
            existing_paths.add(path)
        return merged_diff

    @classmethod
    def build_snapshot_path_index(cls, snapshot: Any) -> ApiConfigSnapshotPathIndex:
        total_occurrences = Counter()

        def visit(value: Any, path: str):
            display_path = path or '$'
            total_occurrences[display_path] += 1
            if isinstance(value, dict):
                for key, item in value.items():
                    child_path = f'{path}.{key}' if path else str(key)
                    visit(item, child_path)
            elif isinstance(value, list):
                for index, item in enumerate(value):
                    child_path = f'{path}.{index}' if path else str(index)
                    visit(item, child_path)

        visit(snapshot, '')
        return ApiConfigSnapshotPathIndex(
            total_occurrences=dict(total_occurrences),
        )

    @classmethod
    def sanitize_diff_item(cls, item: dict, before_snapshot: Any, after_snapshot: Any) -> dict:
        safe_item = copy.deepcopy(item)
        path = str(item.get('path') or '')
        path_parts = item.get('_path_segments')
        is_sensitive_boundary = bool(safe_item.pop('_sensitive_boundary', False))
        safe_item.pop('_path_segments', None)
        if is_sensitive_boundary:
            safe_item['masked'] = True
            return safe_item
        if item.get('type') == 'changed':
            safe_item['before'], safe_item['after'], masked = cls.sanitize_diff_value_pair(
                item.get('before'),
                item.get('after'),
                path,
                before_snapshot,
                after_snapshot,
                path_parts,
            )
            if masked:
                safe_item['masked'] = True
            return safe_item
        masked = False
        if item.get('type') != 'added':
            safe_item['before'], masked = cls.sanitize_diff_value(
                item.get('before'),
                path,
                before_snapshot,
                path_parts,
            )
        if item.get('type') != 'removed':
            safe_item['after'], after_masked = cls.sanitize_diff_value(
                item.get('after'),
                path,
                after_snapshot,
                path_parts,
            )
            masked = masked or after_masked
        if masked:
            safe_item['masked'] = True
        return safe_item

    @classmethod
    def sanitize_diff_value_pair(
            cls,
            before: Any,
            after: Any,
            path: str,
            before_snapshot: Any,
            after_snapshot: Any,
            path_parts: tuple[str, ...] | None = None,
    ) -> tuple[Any, Any, bool]:
        if path_parts is None:
            path_parts = () if path in ('', '$') else tuple(path.split('.'))
        key = path_parts[-1] if path_parts else ''
        if ApiConfigSnapshotService.is_sensitive_key(key):
            return '***', '***', True
        if key == 'value':
            before_parent = cls.resolve_snapshot_path(before_snapshot, path_parts[:-1])
            after_parent = cls.resolve_snapshot_path(after_snapshot, path_parts[:-1])
            if (
                    ApiConfigSnapshotService.has_sensitive_semantic_key(before_parent) or
                    ApiConfigSnapshotService.has_sensitive_semantic_key(after_parent)
            ):
                return '***', '***', True
        return cls.sanitize_snapshot_pair(before, after)

    @classmethod
    def sanitize_diff_value(
            cls,
            value: Any,
            path: str,
            snapshot: Any,
            path_parts: tuple[str, ...] | None = None,
    ) -> tuple[Any, bool]:
        if path_parts is None:
            path_parts = () if path in ('', '$') else tuple(path.split('.'))
        key = path_parts[-1] if path_parts else ''
        if key == 'value':
            parent = cls.resolve_snapshot_path(snapshot, path_parts[:-1])
            if ApiConfigSnapshotService.has_sensitive_semantic_key(parent):
                return '***', True
        return (
            ApiConfigSnapshotService.sanitize_value(copy.deepcopy(value), key),
            ApiConfigSnapshotService.is_sensitive_key(key) or
            ApiConfigSnapshotService.contains_sensitive_structure(value),
        )

    @classmethod
    def resolve_snapshot_path(cls, snapshot: Any, path_parts: tuple[str, ...]) -> Any:
        current = snapshot
        for part in path_parts:
            if isinstance(current, dict):
                if part not in current:
                    return cls._MISSING
                current = current[part]
                continue
            if isinstance(current, list) and part.isdigit():
                index = int(part)
                if index >= len(current):
                    return cls._MISSING
                current = current[index]
                continue
            return cls._MISSING
        return current

    @classmethod
    def diff_snapshots(cls, before: Any, after: Any, path: str = '') -> list[dict]:
        path_segments = () if not path else tuple(path.split('.'))
        return [
            {
                key: value
                for key, value in item.items()
                if not key.startswith('_')
            }
            for item in cls._diff_snapshots(before, after, path, path_segments)
        ]

    @classmethod
    def diff_snapshots_with_segments(cls, before: Any, after: Any) -> list[dict]:
        return cls._diff_snapshots(before, after, '', ())

    @classmethod
    def _diff_snapshots(
            cls,
            before: Any,
            after: Any,
            path: str,
            path_segments: tuple[str, ...],
    ) -> list[dict]:
        if before is cls._MISSING and after is cls._MISSING:
            return []
        if before is cls._MISSING:
            return [{
                'path': path or '$',
                'type': 'added',
                'before': None,
                'after': after,
                '_path_segments': path_segments,
            }]
        if after is cls._MISSING:
            return [{
                'path': path or '$',
                'type': 'removed',
                'before': before,
                'after': None,
                '_path_segments': path_segments,
            }]
        if isinstance(before, dict) and isinstance(after, dict):
            diff = []
            for key in sorted(set(before.keys()) | set(after.keys())):
                child_path = f'{path}.{key}' if path else str(key)
                before_item = before.get(key, cls._MISSING)
                after_item = after.get(key, cls._MISSING)
                child_segments = path_segments + (str(key),)
                if (
                        cls.is_sensitive_boundary_child(before, key) or
                        cls.is_sensitive_boundary_child(after, key)
                ):
                    diff.extend(cls.diff_sensitive_boundary(
                        before_item,
                        after_item,
                        child_path,
                        child_segments,
                    ))
                else:
                    diff.extend(cls._diff_snapshots(
                        before_item,
                        after_item,
                        child_path,
                        child_segments,
                    ))
            return diff
        if isinstance(before, list) and isinstance(after, list):
            diff = []
            for index in range(max(len(before), len(after))):
                before_item = before[index] if index < len(before) else cls._MISSING
                after_item = after[index] if index < len(after) else cls._MISSING
                child_path = f'{path}.{index}' if path else str(index)
                diff.extend(cls._diff_snapshots(
                    before_item,
                    after_item,
                    child_path,
                    path_segments + (str(index),),
                ))
            return diff
        if before == after:
            return []
        return [{
            'path': path or '$',
            'type': 'changed',
            'before': before,
            'after': after,
            '_path_segments': path_segments,
        }]

    @classmethod
    def is_sensitive_boundary_child(cls, parent: Any, key: Any) -> bool:
        if not isinstance(parent, dict) or key not in parent:
            return False
        return (
                ApiConfigSnapshotService.is_sensitive_key(str(key)) or
                (key == 'value' and ApiConfigSnapshotService.has_sensitive_semantic_key(parent))
        )

    @classmethod
    def diff_sensitive_boundary(
            cls,
            before: Any,
            after: Any,
            path: str,
            path_segments: tuple[str, ...],
    ) -> list[dict]:
        before_exists = before is not cls._MISSING
        after_exists = after is not cls._MISSING
        if before_exists and after_exists and before == after:
            return []
        diff_type = 'changed'
        if not before_exists:
            diff_type = 'added'
        elif not after_exists:
            diff_type = 'removed'
        return [{
            'path': path or '$',
            'type': diff_type,
            'before': '***' if before_exists else None,
            'after': '***' if after_exists else None,
            '_path_segments': path_segments,
            '_sensitive_boundary': True,
        }]
