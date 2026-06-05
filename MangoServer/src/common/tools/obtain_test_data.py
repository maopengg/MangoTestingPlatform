# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-19 11:36
# @Author : 毛鹏
import os
import traceback
import uuid
from typing import Any

import minio.error
from mangotools.data_processor import DataProcessor
from mangotools.decorator import data_method
from mangotools.models import MethodModel

from src.apps.auto_system.models import FileData
from src.common.exceptions import ERROR_MSG_0024, ToolsError, ERROR_MSG_0019
from src.common.tools import project_dir
from src.common.tools.view.snowflake import Snowflake


class ObtainTestData(DataProcessor):
    """自定义方法"""

    DATA_FACTORY_PREFIX = 'df.'
    JS_SAFE_INTEGER_MAX = 9007199254740991
    JS_SAFE_INTEGER_MIN = -9007199254740991

    def __init__(self):
        super().__init__()
        self._data_factory_cache: dict[str, Any] = {}

    @classmethod
    @data_method('data', '自定义测试数据', '自定义测试数据示例', [
        MethodModel(f='demo1', n='示例参数1', p='请输入示例参数1', d=True, v='demo1'),
        MethodModel(f='demo2', n='示例参数2', p='请输入示例参数2', d=True, v='demo2'),
    ], sort=0)
    def random_demo(cls, demo1, demo2) -> str:
        """自定义测试数据示例，参数：demo1，demo2"""
        # 自定义测试数据方法需要写在 ObtainTestData 类中。
        # 方法名必须全局唯一，不能和已有测试数据方法重复。
        # 方法必须返回一个值，返回值会作为 ${{方法名()}} 的替换结果。
        # 参数会按字符串传入；需要其他类型时，在方法内部自行转换。
        # 如需给 UI 自动化执行器使用，执行器侧也需要同步增加同名方法。
        print(demo1, demo2)
        return str(uuid.uuid4())

    @classmethod
    @data_method('data', '自定义测试数据', '雪花算法ID', sort=1)
    def number_snowflake_id(cls) -> str:
        """雪花算法ID"""
        return str(Snowflake.snowflake_id())

    @classmethod
    @data_method('data', '自定义测试数据', '获取上传文件', [
        MethodModel(f='file_name', n='文件名称', p='请输入已上传的文件名称', d=True, v='文件名称'),
    ], sort=2)
    def get_file(cls, file_name) -> str:
        """传入文件名称，返回文件对象，参数file_name"""
        file_path = os.path.join(project_dir.upload(), file_name)
        try:
            file_data = FileData.objects.get(name=file_name)
            if not file_data.test_file:
                raise ToolsError(*ERROR_MSG_0019, value=(file_name,))

            with file_data.test_file.open('rb') as remote_file:
                with open(file_path, 'wb') as local_file:
                    for chunk in remote_file.chunks(chunk_size=8192):
                        local_file.write(chunk)

            return str(file_path)
        except FileData.DoesNotExist:
            raise ToolsError(*ERROR_MSG_0019, value=(file_name,))
        except minio.error.S3Error as error:
            traceback.print_exc()
            if getattr(error, 'code', '') == 'NoSuchKey':
                raise ToolsError(*ERROR_MSG_0019, value=(file_name,))
            raise ToolsError(*ERROR_MSG_0024, value=(file_name,))
        except OSError:
            traceback.print_exc()
            raise ToolsError(*ERROR_MSG_0024, value=(file_name,))

    def get_cache(self, key: str) -> Any:
        """优先读取数据工厂缓存，再读取普通缓存。"""
        if key.startswith(self.DATA_FACTORY_PREFIX):
            return self._data_factory_cache.get(key.removeprefix(self.DATA_FACTORY_PREFIX))
        if key in self._data_factory_cache:
            return self._data_factory_cache.get(key)
        return super().get_cache(key)

    def set_data_factory_cache(self, key: str, value: Any) -> None:
        """设置数据工厂专用缓存，不写入普通缓存页签。"""
        if not key:
            return
        key = key.removeprefix(self.DATA_FACTORY_PREFIX)
        self._data_factory_cache[key] = value

    def get_data_factory_all(self) -> dict[str, Any]:
        """获取全部数据工厂缓存数据。"""
        return {key: self.to_frontend_safe_value(value) for key, value in self._data_factory_cache.items()}

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


if __name__ == '__main__':
    test_data = ObtainTestData()
    print(test_data.replace("${{random_demo()}}"))
