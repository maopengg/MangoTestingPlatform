from collections.abc import Callable
from copy import deepcopy
from typing import Any

from rest_framework import serializers

MAX_RELATED_REPRESENTATIONS = 256


class RelatedObjectField(serializers.Field):
    """使用所属 App 提供的格式化函数输出只读关联对象。"""

    def __init__(self, *, formatter: Callable[[Any], Any], many: bool = False,
                 cache_representation: bool = False, **kwargs):
        self.formatter = formatter
        self.many = many
        self.cache_representation = cache_representation
        kwargs.setdefault("read_only", True)
        super().__init__(**kwargs)

    def to_representation(self, value):
        if self.many:
            values = value.all() if hasattr(value, "all") else value
            return [self._format(item) for item in values]
        return self._format(value) if value is not None else None

    def _format(self, value):
        if not self.cache_representation or getattr(value, 'pk', None) is None:
            return self.formatter(value)
        cache = self.context.setdefault('_mango_related_representation_cache', {})
        key = (self.formatter, value._state.db, value._meta.label_lower, value.pk)
        if key not in cache:
            if len(cache) >= MAX_RELATED_REPRESENTATIONS:
                return self.formatter(value)
            cache[key] = self.formatter(value)
        # 同一列表项中的后续处理不能污染其他行或下一次请求。
        return deepcopy(cache[key])
