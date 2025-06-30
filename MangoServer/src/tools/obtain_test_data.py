# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-19 11:36
# @Author : 毛鹏
import os
import shutil
from urllib.parse import urljoin

import requests
from mangotools.data_processor import DataProcessor
from requests.exceptions import MissingSchema

from src.auto_test.auto_system.models import FileData
from src.exceptions import ERROR_MSG_0025, ERROR_MSG_0024, ToolsError, ERROR_MSG_0019, ERROR_MSG_0020
from src.settings import IS_MINIO
from src.tools import project_dir


class ObtainTestData(DataProcessor):

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
            response = requests.get(url, proxies={'http': None, 'https': None}, )
            try:
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


if __name__ == '__main__':
    pass
