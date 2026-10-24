import ast
import re
from typing import Any

PERF_FUNCTION_ARGUMENTS = {
    "perf_uuid": (), "perf_snowflake_id": (), "perf_timestamp_ms": (),
    "perf_timestamp_s": (), "perf_trace_id": (), "perf_uuid_hex": (),
    "perf_random_email": (),
    "perf_random_string": (("length", 12),),
    "perf_random_digits": (("length", 8),),
    "perf_random_hex": (("length", 16),),
    "perf_random_lowercase": (("length", 12),),
    "perf_random_int": (("left", 0), ("right", 1000000)),
    "perf_unique_string": (("prefix", "perf"),),
}

_PLACEHOLDER = re.compile(r"\$\{\{([^{}]*)\}\}")
_FUNCTION_START = re.compile(r"\$\{\{\s*[A-Za-z_]\w*\s*\(")
_CACHE_KEY = re.compile(r"[A-Za-z_]\w*")


def _parse_call(expression: str) -> dict:
    call_text, separator, cache_key = expression.partition("|")
    if separator and not _CACHE_KEY.fullmatch(cache_key.strip()):
        raise ValueError("缓存变量名只能包含字母、数字和下划线")
    try:
        call = ast.parse(call_text.strip(), mode="eval").body
    except SyntaxError as exc:
        raise ValueError("函数表达式语法无效") from exc
    if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name):
        raise ValueError("函数表达式必须是直接函数调用")
    name = call.func.id
    if name not in PERF_FUNCTION_ARGUMENTS:
        raise ValueError(f"函数 {name} 尚未支持性能测试")
    definition = PERF_FUNCTION_ARGUMENTS[name]
    if len(call.args) > len(definition):
        raise ValueError(f"函数 {name} 参数过多")
    result = {key: default for key, default in definition}
    assigned = set()
    for (key, _), arg in zip(definition, call.args):
        result[key] = _literal(arg)
        assigned.add(key)
    for keyword in call.keywords:
        if keyword.arg not in result or keyword.arg in assigned:
            raise ValueError(f"函数 {name} 包含未知或重复参数")
        result[keyword.arg] = _literal(keyword.value)
        assigned.add(keyword.arg)
    if name.startswith("perf_random_") and "length" in result:
        result["length"] = _bounded_int(result["length"], 1, 256, "length")
    if name == "perf_random_int":
        result["left"] = _bounded_int(result["left"], -9007199254740991, 9007199254740991, "left")
        result["right"] = _bounded_int(result["right"], -9007199254740991, 9007199254740991, "right")
        if result["left"] > result["right"]:
            raise ValueError("left 不能大于 right")
        if result["right"] - result["left"] >= 9007199254740991:
            raise ValueError("随机整数范围跨度超出安全整数范围")
    if name == "perf_unique_string":
        prefix = str(result["prefix"])
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", prefix):
            raise ValueError("prefix 只能包含字母、数字、下划线和连字符，长度 1～32")
        result["prefix"] = prefix
    return {"name": name, "args": result, "cache_key": cache_key.strip() if separator else None}


def _literal(node: ast.AST) -> Any:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Constant) and isinstance(node.value, (str, int)) and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub) and isinstance(node.operand,
                                                                                      ast.Constant) and type(
        node.operand.value) is int:
        return -node.operand.value
    raise ValueError("性能函数参数只支持固定字符串或整数，不支持嵌套调用")


def _bounded_int(value: Any, minimum: int, maximum: int, label: str) -> int:
    try:
        normalized = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} 必须是整数") from exc
    if not minimum <= normalized <= maximum:
        raise ValueError(f"{label} 超出允许范围 {minimum}～{maximum}")
    return normalized


def collect_perf_functions(payload: Any) -> list[dict]:
    """Validate every function placeholder and return runtime lookup entries."""
    functions: dict[str, dict] = {}

    def visit(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                visit(item, f"{path}.{key}")
        elif isinstance(value, list):
            for index, item in enumerate(value):
                visit(item, f"{path}[{index}]")
        elif isinstance(value, str):
            matches = list(_PLACEHOLDER.finditer(value))
            for start in _FUNCTION_START.finditer(value):
                if not any(match.start() == start.start() for match in matches):
                    raise ValueError(f"{path} 包含无法解析的函数表达式")
            for match in matches:
                expression = match.group(1).strip()
                if "(" not in expression and ")" not in expression:
                    continue
                try:
                    spec = _parse_call(expression)
                except ValueError as exc:
                    raise ValueError(f"{path} 的 {match.group(0)}：{exc}") from exc
                functions[match.group(0)] = {"expression": match.group(0), **spec}

    visit(payload, "Case")
    return list(functions.values())
