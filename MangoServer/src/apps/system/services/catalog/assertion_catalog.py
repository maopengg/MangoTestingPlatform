import json
from copy import deepcopy

from src.apps.system.enums import CacheDataKey2Enum
from src.apps.system.services.configuration.cache_data_value import CacheDataValue
from src.common.testing import assertion_func_info


class AssertionCatalogService:
    """Build the assertion catalog consumed by shared frontend editors."""

    OPERATION_GROUPS = {"web", "android"}
    UI_GROUPS = {
        "ass_web": ("Web UI断言", "web"),
        "ass_android": ("Android UI断言", "android"),
    }
    OBJECT_FIELD_NAMES = {
        "min": "最小值",
        "max": "最大值",
        "value": "目标值",
        "tolerance": "允许误差",
        "tolerance_seconds": "允许秒数误差",
        "text": "目标文本",
        "count": "次数",
        "key": "字段名",
        "field": "字段名",
        "values": "值列表",
        "name": "名称",
        "id": "ID",
        "status": "状态",
        "path": "路径",
        "pattern": "匹配规则",
        "start": "开始值",
        "end": "结束值",
    }
    OBJECT_FIELD_TYPES = {
        "第几行": "number",
        "预期行数": "number",
        "预期列数": "number",
        "最少行数": "number",
        "最多行数": "number",
        "最少列数": "number",
        "最多列数": "number",
        "预期次数": "number",
        "最少次数": "number",
        "最多次数": "number",
        "行数据": "json",
        "预期值列表": "array",
        "预期表头": "array",
        "工作表列表": "array",
        "values": "array",
    }

    @classmethod
    def catalog(cls) -> list[dict]:
        stored_tree = CacheDataValue.get_cache_value(
            CacheDataKey2Enum.SELECT_VALUE.value
        )
        source_tree = stored_tree if isinstance(stored_tree, list) else []
        groups = [
            cls._normalize_group(item)
            for item in source_tree
            if isinstance(item, dict) and item.get("value") not in cls.OPERATION_GROUPS
        ]
        groups = [item for item in groups if item and item.get("children")]

        known_values = {item.get("value") for item in groups}
        for item in assertion_func_info:
            if not isinstance(item, dict) or item.get("value") in known_values:
                continue
            normalized = cls._normalize_group(item)
            if normalized and normalized.get("children"):
                groups.append(normalized)
        return groups

    @classmethod
    def _normalize_group(cls, group: dict) -> dict | None:
        value = str(group.get("value") or "").strip()
        if not value:
            return None
        if value in cls.UI_GROUPS:
            label, scope = cls.UI_GROUPS[value]
            testable = False
            reason = "UI 自动化断言依赖页面或元素上下文，只能在 UI 用例运行时验证"
        elif value == "sql断言":
            label, scope = group.get("label") or value, "mysql"
            testable = False
            reason = "MySQL 断言依赖数据库查询结果，只能在用例运行时验证"
        else:
            label, scope = group.get("label") or value, "public"
            testable = True
            reason = ""

        class_groups = deepcopy(group.get("children") or [])
        normalized = {
            **deepcopy(group),
            "label": label,
            "value": value,
            "scope": scope,
            "testable": testable,
            "children": [],
        }
        for class_group in class_groups:
            if not isinstance(class_group, dict):
                continue
            methods = []
            for method in class_group.get("children") or []:
                parameters = [
                    cls._normalize_parameter(parameter, file_assertion=value == "文件断言")
                    for parameter in deepcopy(method.get("parameter") or [])
                    if isinstance(parameter, dict)
                ]
                methods.append({
                    **method,
                    "parameter": parameters,
                    "scope": scope,
                    "testable": testable,
                    "test_disabled_reason": reason,
                })
            normalized["children"].append({
                **class_group,
                "scope": scope,
                "testable": testable,
                "children": methods,
            })
        return normalized

    @classmethod
    def _normalize_parameter(cls, parameter: dict, *, file_assertion: bool) -> dict:
        result = deepcopy(parameter)
        example = result.get("v")
        structured_example = cls._structured_example(example)
        if isinstance(structured_example, dict):
            result["example_as_placeholder"] = True
            result["object_fields"] = result.get("object_fields") or [
                {
                    "f": str(field),
                    "n": cls.OBJECT_FIELD_NAMES.get(str(field), str(field)),
                    "p": cls._field_placeholder(field_example),
                    "value_type": cls.OBJECT_FIELD_TYPES.get(
                        str(field), cls._field_value_type(field_example)
                    ),
                }
                for field, field_example in structured_example.items()
            ]
        elif file_assertion:
            result["example_as_placeholder"] = True
        return result

    @staticmethod
    def _structured_example(example):
        if isinstance(example, dict):
            return example
        if not isinstance(example, str) or not example.strip().startswith("{"):
            return None
        try:
            parsed = json.loads(example)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None

    @staticmethod
    def _field_placeholder(example) -> str:
        if isinstance(example, (dict, list)):
            return json.dumps(example, ensure_ascii=False)
        return str(example) if example is not None else ""

    @staticmethod
    def _field_value_type(example) -> str:
        if isinstance(example, bool):
            return "boolean"
        if isinstance(example, (int, float)):
            return "number"
        if isinstance(example, list):
            return "array"
        if isinstance(example, dict):
            return "object"
        return "string"
