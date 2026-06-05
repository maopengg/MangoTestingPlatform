from __future__ import annotations

import re

from mangotools.decorator import get_data_method_info

from src.common.exceptions import MangoServerError
from src.services.mcp_server.common import fail, ok
from src.common.tools.obtain_test_data import ObtainTestData


def _normalize_expression(expression: str) -> str:
    value = (expression or "").strip()
    if value.startswith("${{") and value.endswith("}}"):
        return value[3:-2].strip()
    if value.startswith("${") and value.endswith("}"):
        return value[2:-1].strip()
    return value


def _method_groups() -> list[dict]:
    return get_data_method_info()


def _is_test_data_group(type_group: dict) -> bool:
    return type_group.get("value") == "data"


def _example_parameter_value(key: str) -> str:
    examples = {
        "length": "8",
        "left": "1",
        "right": "100",
        "digits": "3",
        "count": "3",
        "days": "0",
        "day": "0",
        "hours": "0",
        "hour": "0",
        "minutes": "0",
        "minute": "0",
        "seconds": "0",
        "second": "0",
        "extension": "txt",
        "file_name": "文件名称",
        "time_parts": "12:30:00",
        "demo1": "demo1",
        "demo2": "demo2",
    }
    return examples.get(key, key)


def _build_example(method: dict) -> str:
    name = method.get("value") or ""
    parameters = method.get("parameter") or []
    if isinstance(parameters, dict):
        values = [
            value if value is not None else _example_parameter_value(key)
            for key, value in parameters.items()
        ]
    else:
        values = [
            str(item.get("v") if item.get("v") is not None else _example_parameter_value(item.get("f") or ""))
            for item in parameters
        ]
    return "${{" + f"{name}({', '.join(values)})" + "}}"


def _build_expression_template(method: dict) -> str:
    name = method.get("value") or ""
    parameters = method.get("parameter") or []
    if isinstance(parameters, dict):
        args = [str(key) for key in parameters.keys()]
    else:
        args = [str(item.get("f") or "") for item in parameters if item.get("f")]
    return "${{" + f"{name}({', '.join(args)})" + "}}"


def register_system_variable_tools(mcp):
    @mcp.tool()
    def list_test_data_methods(keyword: str | None = None, include_hidden: bool = False) -> dict:
        """查询平台变量/随机测试数据方法，等同于 GET /system/variable/random/list。

        只返回测试数据分类下的方法，结构按 type_group -> class_group -> method 分组；
        type_label/class_label 可作为测试数据类型展示，method 是可调用的具体方法。
        expression_template 是参数名表达式模板，example 是示例值表达式。

        数据工厂字符串类字段优先使用这些方法生成：
        generator_type=13，generator_config={"value": "${{方法名(...)}}"}。
        """
        hidden_custom_methods = {
            "set_data_factory_cache",
            "get_data_factory_all()",
            "get_data_factory_all",
            "to_frontend_safe_value",
        }
        keyword_value = (keyword or "").strip().lower()
        groups = []
        for type_group in _method_groups():
            if not _is_test_data_group(type_group):
                continue
            class_groups = []
            for class_group in type_group.get("children") or []:
                methods = []
                for method in class_group.get("children") or []:
                    if not include_hidden and method.get("value") in hidden_custom_methods:
                        continue
                    search_text = " ".join(
                        str(part or "")
                        for part in [
                            type_group.get("label"),
                            type_group.get("value"),
                            class_group.get("label"),
                            class_group.get("value"),
                            method.get("label"),
                            method.get("value"),
                            method.get("parameter"),
                        ]
                    ).lower()
                    if keyword_value and keyword_value not in search_text:
                        continue
                    method_data = dict(method)
                    method_data["type"] = type_group.get("value")
                    method_data["type_label"] = type_group.get("label")
                    method_data["class_name"] = class_group.get("value")
                    method_data["class_label"] = class_group.get("label")
                    method_data["expression_template"] = _build_expression_template(method_data)
                    method_data["example"] = _build_example(method_data)
                    methods.append(method_data)
                if methods:
                    class_data = dict(class_group)
                    class_data["children"] = methods
                    class_data["count"] = len(methods)
                    class_groups.append(class_data)
            if class_groups:
                group_data = dict(type_group)
                group_data["children"] = class_groups
                group_data["count"] = sum(item["count"] for item in class_groups)
                groups.append(group_data)
        return ok({"items": groups, "count": sum(item["count"] for item in groups)})

    @mcp.tool()
    def evaluate_test_data_expression(expression: str) -> dict:
        """试算一个平台变量表达式，等同于 GET /system/variable/value?name=${{...}}。"""
        normalized = _normalize_expression(expression)
        if not normalized:
            return fail("请输入需要测试的方法", "TEST_DATA_EXPRESSION_EMPTY")
        if not re.search(r"\((.*?)\)", normalized):
            return fail("变量表达式必须包含方法调用，例如 ${{random_string(8)}}", "INVALID_TEST_DATA_EXPRESSION")
        try:
            value = ObtainTestData().regular(normalized)
        except MangoServerError as error:
            return fail(error.msg, str(error.code))
        return ok(
            {
                "expression": "${{" + normalized + "}}",
                "normalized_expression": normalized,
                "value": str(value),
            },
            "变量表达式执行成功",
        )
