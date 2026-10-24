import re
from typing import Annotated
from pydantic import Field, field_validator
from src.common.schemas.base import StrictSchema


class EvaluationMapping(StrictSchema):
    paths: list[Annotated[str, Field(min_length=1, max_length=512)]] = Field(default_factory=list, max_length=100)

    @field_validator("paths")
    @classmethod
    def validate_paths(cls, value):
        if any(not path.startswith("$") or path != path.strip() for path in value) or len(set(value)) != len(value):
            raise ValueError("JSONPath 必须以 $ 开头，不能重复或包含首尾空白")
        return value


def normalize_output_paths(value):
    if not isinstance(value, dict) or "paths" in value:
        return value
    if value.get("template"):
        raise ValueError("旧输出模板不再支持，请重新填写响应提取 JSONPath")
    if value.get("mode", "identity") not in {"identity", "jsonpath", "select"}:
        raise ValueError("请重新填写响应提取 JSONPath")
    selectors = value.get("selectors") or {}
    if not isinstance(selectors, dict) or any(not isinstance(path, str) for path in selectors.values()):
        raise ValueError("请重新填写响应提取 JSONPath")
    paths = list(selectors.values())
    for collection in (value.get("collections") or {}).values():
        if collection.get("where") or collection.get("cardinality", "many") != "many":
            raise ValueError("请重新填写响应提取 JSONPath")
        path = collection["path"]
        suffix = collection.get("value_path", "$")
        paths.append(path if suffix == "$" else path + "[*]." + suffix.removeprefix("$."))
    return {"paths": [re.sub(r"\.(\d+)(?=\.|$)", r"[\1]", path if path.startswith("$") else "$." + path) for path in paths]}
