# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-19 11:36
# @Author : 毛鹏
import json
import os
import uuid

from mangotools.data_processor import DataProcessor, ObtainRandomData

from src.exceptions import ToolsError, ERROR_MSG_0026
from src.network import HTTP
from src.tools import project_dir
import asyncio
import threading
from typing import Any


def run_async(coro):
    """在同步环境执行 async 并等待结果（兼容已存在事件循环）"""
    result = None
    error = None

    def runner():
        nonlocal result, error
        try:
            result = asyncio.run(coro)
        except Exception as e:
            error = e

    t = threading.Thread(target=runner)
    t.start()
    t.join()

    if error:
        raise error

    return result

class ObtainTestData(DataProcessor):
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
        # 1.必须写在这个类下面，如果需要给UI自动化使用，则执行器也需要写
        # 2.必须要写 """示例方法""" 这种注释
        # 3.函数名称必须是唯一，跟我已使用的不可重复
        # 4.函数必须要返回一个值，返回值就是你需要的随机数据
        # 5.函数如果要接受传值，则直接接收参数，传入进来的参数默认是字符串类型
        print(demo1, demo2)
        return str(uuid.uuid4())

    @classmethod
    def get_file(cls, file_name) -> str:
        """传入文件名称，返回文件"""

        run_async(HTTP.system.download_file(file_name))

        file_path = os.path.join(project_dir.upload(), file_name)

        if os.path.exists(file_path):
            return file_path
        else:
            raise ToolsError(*ERROR_MSG_0026)


if __name__ == '__main__':
    print(json.dumps(ObtainRandomData.get_methods(), ensure_ascii=False))
