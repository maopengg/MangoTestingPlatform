# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-19 11:36
# @Author : 毛鹏
import os
import shutil
import uuid
from urllib.parse import urljoin

import requests
from mangotools.data_processor import DataProcessor
from mangotools.models import FunctionModel
from requests.exceptions import MissingSchema

from src.auto_test.auto_system.models import FileData
from src.exceptions import ERROR_MSG_0025, ERROR_MSG_0024, ToolsError, ERROR_MSG_0019, ERROR_MSG_0020
from src.settings import IS_MINIO
from src.tools import project_dir


class ObtainTestData(DataProcessor):
    """自定义方法"""

    @classmethod
    def random_demo(cls, **kwargs) -> str:
        """示例方法"""
        # 1.必须写在这个类下面，如果需要给UI自动化使用，则执行器也需要写
        # 2.必须要写 """示例方法""" 这种注释
        # 3.函数名称必须是唯一，跟我已使用的不可重复
        # 4.函数必须要返回一个值，返回值就是你需要的随机数据
        # 5.函数如果要接受传值，则默认使用data来接收数据，接收的是一个data的dict类型，示例：kwargs.get('data')
        return str(uuid.uuid4())

    @classmethod
    def get_file(cls, **kwargs) -> str:
        """传入文件名称，返回文件对象"""
        file_name = kwargs.get('data')
        if IS_MINIO:
            from src.settings import MINIO_STORAGE_ENDPOINT
            minio_host = MINIO_STORAGE_ENDPOINT
            if minio_host is None:
                raise ToolsError(*ERROR_MSG_0025)
            url = urljoin(minio_host, f'/mango-file/test_file/{file_name}')
            try:
                response = requests.get(url, proxies={'http': None, 'https': None}, )
                if response.status_code != 200:
                    raise ToolsError(*ERROR_MSG_0024, value=(file_name,))
                file_path = os.path.join(project_dir.upload(), file_name)
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                return str(file_path)
            except FileNotFoundError:
                raise ToolsError(*ERROR_MSG_0020)
            except MissingSchema:
                raise ToolsError(*ERROR_MSG_0019)
        else:
            file_data = FileData.objects.get(name=file_name)
            shutil.copy2(
                str(os.path.join(project_dir.root_path(), 'mango-file', file_data.test_file.path)),
                str(os.path.join(project_dir.upload(), file_name))
            )
            return str(os.path.join(project_dir.upload(), file_name))
