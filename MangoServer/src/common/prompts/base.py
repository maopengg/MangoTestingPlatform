"""提示词目录的数据契约与安全模板渲染。"""

from __future__ import annotations

import re
from typing import Any

_PLACEHOLDER_PATTERN = re.compile(r"{{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*}}")


def render_template(template: str, **variables: Any) -> str:
    """只替换命名占位符，不执行表达式或任意模板代码。"""

    required = set(_PLACEHOLDER_PATTERN.findall(template))
    missing = sorted(required - variables.keys())
    if missing:
        raise ValueError(f"提示词模板缺少变量：{', '.join(missing)}")

    def replace(match: re.Match) -> str:
        value = variables[match.group(1)]
        return "" if value is None else str(value)

    return _PLACEHOLDER_PATTERN.sub(replace, template).strip()
