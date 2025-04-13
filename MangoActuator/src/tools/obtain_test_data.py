# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-19 11:36
# @Author : 毛鹏
import json
import os

from mangokit.data_processor import DataProcessor, ObtainRandomData

from src.exceptions import ToolsError, ERROR_MSG_0026
from src.network import HTTP
from src.tools import project_dir


class ObtainTestData(DataProcessor):

    def __init__(self):
        super().__init__()

    @classmethod
    def get_file(cls, **kwargs) -> str:
        """传入文件名称，返回文件"""
        file_name = kwargs.get('data')
        HTTP.not_auth.download_file(file_name)
        file_path = os.path.join(project_dir.upload(), file_name)
        if os.path.exists(file_path):
            return file_path
        else:
            raise ToolsError(*ERROR_MSG_0026)


if __name__ == '__main__':
    print(json.dumps(ObtainRandomData.get_methods(), ensure_ascii=False))
