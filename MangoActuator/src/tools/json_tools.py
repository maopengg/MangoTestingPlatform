# -*- coding: utf-8 -*-
import json
from typing import Any

from pydantic import BaseModel


def json_dumps(data: Any, *, indent: int | None = None) -> str:
    """Dump JSON text without escaping Chinese characters."""
    if isinstance(data, BaseModel):
        data = data.model_dump(mode='json')
    return json.dumps(data, ensure_ascii=False, indent=indent)
