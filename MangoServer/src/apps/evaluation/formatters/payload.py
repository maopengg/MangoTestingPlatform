import hashlib
import json
from decimal import Decimal
from typing import Any


SENSITIVE_KEYS = {"authorization", "proxy-authorization", "cookie", "token", "v2token", "access_token", "refresh_token", "password", "secret", "api_key", "x-api-key", "x-access-context"}


def is_secret_reference(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    stripped = value.strip()
    return (stripped.startswith("${{") and stripped.endswith("}}")) or stripped.startswith("${secret_required:")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def content_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def mask_sensitive(value: Any):
    if isinstance(value, dict):
        return {
            key: (item if str(key).lower() in SENSITIVE_KEYS and is_secret_reference(item)
                  else "***" if str(key).lower() in SENSITIVE_KEYS else mask_sensitive(item))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [mask_sensitive(item) for item in value]
    return value


def plaintext_secret_paths(value: Any, prefix="") -> list[str]:
    paths = []
    if isinstance(value, dict):
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if str(key).lower() in SENSITIVE_KEYS and item not in (None, "") and not is_secret_reference(item):
                paths.append(path)
            else:
                paths.extend(plaintext_secret_paths(item, path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            paths.extend(plaintext_secret_paths(item, f"{prefix}[{index}]"))
    return paths


def select_value(source: Any, path: str | None, default=None):
    if path in (None, "", "$"):
        return source
    current = source
    normalized = str(path).removeprefix("$.")
    for token in normalized.split("."):
        if token == "":
            continue
        if isinstance(current, dict):
            current = current.get(token, default)
        elif isinstance(current, (list, tuple)):
            try:
                current = current[int(token)]
            except (ValueError, IndexError):
                return default
        else:
            return default
    return current


def apply_mapping(source, mapping):
    from pydantic import ValidationError
    from mangotools.data_processor import JsonTool
    from mangotools.exceptions import MangoToolsError
    from src.apps.evaluation.schemas.mapping import EvaluationMapping
    from src.apps.evaluation.services.validation import invalid_config
    try:
        paths = EvaluationMapping.model_validate(mapping or {}).paths
    except ValidationError as error:
        raise invalid_config("响应提取配置无效，请重新填写 JSONPath") from error
    if not paths:
        return source
    values = []
    for path in paths:
        if path == "$":
            values.append(source)
            continue
        try:
            values.append(JsonTool.get_json_path_value(source, path))
        except MangoToolsError as error:
            raise invalid_config(f"JSONPath 无匹配或格式错误：{path}") from error
    return values[0] if len(values) == 1 else values


def decimal_score(value: float | Decimal | None):
    if value is None:
        return None
    return Decimal(str(round(float(value), 2)))
