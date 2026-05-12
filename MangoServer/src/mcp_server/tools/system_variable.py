from __future__ import annotations

import re

from mangotools.data_processor import ObtainRandomData
from mangotools.method import class_methods, class_own_methods
from mangotools.models import ClassMethodModel

from src.exceptions import MangoServerError
from src.mcp_server.common import fail, ok
from src.tools.obtain_test_data import ObtainTestData


def _normalize_expression(expression: str) -> str:
    value = (expression or "").strip()
    if value.startswith("${{") and value.endswith("}}"):
        return value[3:-2].strip()
    if value.startswith("${") and value.endswith("}"):
        return value[2:-1].strip()
    return value


def _method_groups() -> list[dict]:
    custom_methods = []
    for item in class_own_methods(ObtainTestData):
        if item.label:
            item.label += "()"
        custom_methods.append(item.model_dump())

    custom_group = ClassMethodModel(
        value=ObtainTestData.__name__,
        label=ObtainTestData.__doc__,
        children=custom_methods,
    ).model_dump()
    random_groups = [item.model_dump() for item in class_methods(ObtainRandomData)]
    return [custom_group, *random_groups]


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
    label = method.get("label") or ""
    parameters = method.get("parameter") or {}
    values = [value or _example_parameter_value(key) for key, value in parameters.items()]
    return "${{" + label.replace("()", f"({','.join(values)})") + "}}"


def register_system_variable_tools(mcp):
    @mcp.tool()
    def list_test_data_methods(keyword: str | None = None, include_hidden: bool = False) -> dict:
        """查询平台变量/随机测试数据方法，等同于 GET /system/variable/random/list。"""
        hidden_custom_methods = {
            "get_cache()",
            "set_data_factory_cache()",
            "get_data_factory_all()",
            "to_frontend_safe_value()",
        }
        keyword_value = (keyword or "").strip().lower()
        groups = []
        for group in _method_groups():
            children = []
            for method in group.get("children") or []:
                if not include_hidden and group.get("value") == "ObtainTestData" and method.get("label") in hidden_custom_methods:
                    continue
                search_text = " ".join(
                    str(part or "")
                    for part in [
                        group.get("label"),
                        group.get("value"),
                        method.get("label"),
                        method.get("value"),
                        method.get("parameter"),
                    ]
                ).lower()
                if keyword_value and keyword_value not in search_text:
                    continue
                method_data = dict(method)
                method_data["example"] = _build_example(method_data)
                children.append(method_data)
            if children:
                group_data = dict(group)
                group_data["children"] = children
                group_data["count"] = len(children)
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
