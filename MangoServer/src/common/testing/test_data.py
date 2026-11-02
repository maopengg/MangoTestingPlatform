import re
import uuid
from copy import deepcopy
from contextlib import contextmanager
from typing import Any

from mangotools.data_processor import DataProcessor
from mangotools.decorator import data_method
from mangotools.models import MethodModel

from src.common.testing.perf_test_data import PerfTestDataMethods
from src.common.utils.snowflake import Snowflake


class ObtainTestData(PerfTestDataMethods, DataProcessor):
    """自定义测试数据方法"""

    DATA_FACTORY_PREFIX = 'df.'
    JS_SAFE_INTEGER_MAX = 9007199254740991
    JS_SAFE_INTEGER_MIN = -9007199254740991
    SIMPLE_CACHE_EXPRESSION = re.compile(r'\$\{\{\s*([^{}|()]+?)\s*\}\}')

    def __init__(self):
        super().__init__()
        self._data_factory_cache: dict[str, Any] = {}
        self._preserve_unresolved_cache_placeholders = False

    @contextmanager
    def preserve_unresolved_cache_placeholders(self):
        """单 API 调试时保留未知缓存变量，其他执行链路仍严格校验。"""
        previous = self._preserve_unresolved_cache_placeholders
        self._preserve_unresolved_cache_placeholders = True
        try:
            yield
        finally:
            self._preserve_unresolved_cache_placeholders = previous

    def replace(self, data: list | dict | str | None) -> list | dict | str | None:
        if not self._preserve_unresolved_cache_placeholders:
            return super().replace(data)
        if isinstance(data, list):
            return [self.replace(item) for item in data]
        if isinstance(data, dict):
            return {self.replace(key): self.replace(value) for key, value in data.items()}
        if not isinstance(data, str):
            return super().replace(data)

        protected: dict[str, str] = {}

        def protect_missing(match: re.Match) -> str:
            key = match.group(1).strip()
            if self.has_cache(key):
                return match.group(0)
            token = f'__MANGO_UNRESOLVED_CACHE_{uuid.uuid4().hex}__'
            protected[token] = match.group(0)
            return token

        masked = self.SIMPLE_CACHE_EXPRESSION.sub(protect_missing, data)
        replaced = super().replace(masked)
        if not isinstance(replaced, str):
            return replaced
        for token, expression in protected.items():
            replaced = replaced.replace(token, expression)
        return replaced

    @classmethod
    @data_method('data', '自定义测试数据', '自定义测试数据示例', [
        MethodModel(f='demo1', n='示例参数1', p='请输入示例参数1', d=True, v='demo1'),
        MethodModel(f='demo2', n='示例参数2', p='请输入示例参数2', d=True, v='demo2'),
    ], sort=0)
    def random_demo(cls, demo1, demo2) -> str:
        """自定义测试数据示例，参数：demo1，demo2"""
        print(demo1, demo2)
        return str(uuid.uuid4())

    @classmethod
    @data_method('data', '自定义测试数据', '雪花算法ID', sort=1)
    def number_snowflake_id(cls) -> str:
        """雪花算法ID"""
        return str(Snowflake.snowflake_id())

    def get_cache(self, key: str) -> Any:
        """优先读取数据工厂缓存，再读取普通缓存。"""
        if key.startswith(self.DATA_FACTORY_PREFIX):
            return self._data_factory_cache.get(key.removeprefix(self.DATA_FACTORY_PREFIX))
        if key in self._data_factory_cache:
            return self._data_factory_cache.get(key)
        return super().get_cache(key)

    def has_cache(self, key: str) -> bool:
        """数据工厂缓存和普通缓存都可参与请求变量替换。"""
        if key.startswith(self.DATA_FACTORY_PREFIX):
            return key.removeprefix(self.DATA_FACTORY_PREFIX) in self._data_factory_cache
        return key in self._data_factory_cache or super().has_cache(key)

    def set_data_factory_cache(self, key: str, value: Any) -> None:
        """设置数据工厂专用缓存，不写入普通缓存页签。"""
        if not key:
            return
        key = key.removeprefix(self.DATA_FACTORY_PREFIX)
        self._data_factory_cache[key] = value

    def get_data_factory_all(self) -> dict[str, Any]:
        """获取全部数据工厂缓存数据。"""
        return {key: self.to_frontend_safe_value(value) for key, value in self._data_factory_cache.items()}

    def get_data_factory_snapshot(self) -> dict[str, Any]:
        """内部执行快照保留原始类型，不能复用面向前端的大整数展示转换。"""
        return deepcopy(self._data_factory_cache)

    @classmethod
    def to_frontend_safe_value(cls, value: Any) -> Any:
        """前端 JSON 解析会丢失超大整数精度，展示数据转字符串更安全。"""
        if isinstance(value, bool):
            return value
        if isinstance(value, int) and not cls.JS_SAFE_INTEGER_MIN <= value <= cls.JS_SAFE_INTEGER_MAX:
            return str(value)
        if isinstance(value, dict):
            return {key: cls.to_frontend_safe_value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [cls.to_frontend_safe_value(item) for item in value]
        return value
