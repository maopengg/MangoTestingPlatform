# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-12-21 11:15
# @Author : 毛鹏
import os

from src.exceptions.error_msg import ERROR_MSG_0026
from src.exceptions.tools_exception import FileDoesNotEexistError
from src.network import Http
from src.tools import InitPath


class RandomFileData:
    """获取文件对象"""

    @classmethod
    def get_file(cls, **kwargs) -> str:
        """传入文件名称，返回文件"""
        file_name = kwargs.get('data')
        Http.download_file(file_name)
        file_path = os.path.join(InitPath.upload_files, file_name)
        if os.path.exists(file_path):
            return file_path
        else:
            raise FileDoesNotEexistError(*ERROR_MSG_0026)
