"""ES 精确目标契约，工厂与 API 资源规则共用。"""
from typing import Annotated

from pydantic import StringConstraints


EsIndexTemplate = Annotated[str, StringConstraints(
    min_length=1, max_length=200,
    pattern=r'^(?:\{tenant\}|[a-z0-9][a-z0-9_-]*(?:\{tenant\})?)$',
)]
