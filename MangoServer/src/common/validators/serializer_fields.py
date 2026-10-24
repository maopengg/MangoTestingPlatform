from collections.abc import Callable
from typing import Any

from rest_framework import serializers


class RelatedObjectField(serializers.Field):
    """使用所属 App 提供的格式化函数输出只读关联对象。"""

    def __init__(self, *, formatter: Callable[[Any], Any], many: bool = False, **kwargs):
        self.formatter = formatter
        self.many = many
        kwargs.setdefault("read_only", True)
        super().__init__(**kwargs)

    def to_representation(self, value):
        if self.many:
            values = value.all() if hasattr(value, "all") else value
            return [self.formatter(item) for item in values]
        return self.formatter(value) if value is not None else None
