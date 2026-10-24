# -*- coding: utf-8 -*-
import asyncio
import os
import threading
import uuid
from typing import Any

from mangotools.data_processor import DataProcessor

from src.exceptions import ERROR_MSG_0026, ToolsError
from src.network import HTTP
from src.tools import project_dir


def run_async(coro):
    result = None
    error = None

    def runner():
        nonlocal result, error
        try:
            result = asyncio.run(coro)
        except Exception as err:
            error = err

    thread = threading.Thread(target=runner)
    thread.start()
    thread.join()

    if error:
        raise error

    return result


class ObtainTestData(DataProcessor):
    """自定义测试数据方法"""

    DATA_FACTORY_PREFIX = 'df.'
    JS_SAFE_INTEGER_MAX = 9007199254740991
    JS_SAFE_INTEGER_MIN = -9007199254740991

    def __init__(self):
        super().__init__()
        self._data_factory_cache: dict[str, Any] = {}

    def get_cache(self, key: str) -> Any:
        if key.startswith(self.DATA_FACTORY_PREFIX):
            return self._data_factory_cache.get(key.removeprefix(self.DATA_FACTORY_PREFIX))
        if key in self._data_factory_cache:
            return self._data_factory_cache.get(key)
        return super().get_cache(key)

    def has_cache(self, key: str) -> bool:
        if key.startswith(self.DATA_FACTORY_PREFIX):
            return key.removeprefix(self.DATA_FACTORY_PREFIX) in self._data_factory_cache
        return key in self._data_factory_cache or super().has_cache(key)

    def set_data_factory_cache(self, key: str, value: Any) -> None:
        if not key:
            return
        self._data_factory_cache[key.removeprefix(self.DATA_FACTORY_PREFIX)] = value

    def get_data_factory_all(self) -> dict[str, Any]:
        return {key: self.to_frontend_safe_value(value) for key, value in self._data_factory_cache.items()}

    @classmethod
    def to_frontend_safe_value(cls, value: Any) -> Any:
        if isinstance(value, bool):
            return value
        if isinstance(value, int) and not cls.JS_SAFE_INTEGER_MIN <= value <= cls.JS_SAFE_INTEGER_MAX:
            return str(value)
        if isinstance(value, dict):
            return {key: cls.to_frontend_safe_value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [cls.to_frontend_safe_value(item) for item in value]
        return value

    @classmethod
    def random_demo(cls, demo1, demo2) -> str:
        """示例方法"""
        return str(uuid.uuid4())

    @classmethod
    def get_file_by_id(cls, file_id) -> str:
        """传入测试文件ID，下载并返回本地文件路径"""
        file_path = run_async(HTTP.system.download_file_by_id_isolated(file_id))
        if file_path and os.path.exists(file_path):
            return file_path
        raise ToolsError(*ERROR_MSG_0026)
