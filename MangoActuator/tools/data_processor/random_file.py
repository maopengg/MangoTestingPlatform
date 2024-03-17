# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-12-21 11:15
# @Author : 毛鹏
import os
from typing import BinaryIO

from exceptions.tools_exception import FileDoesNotEexistError
from service.http_client.http_api import HttpApi
from tools import Initialization
from tools.message.error_msg import ERROR_MSG_0026


class RandomFileData:
    """获取文件对象"""

    @classmethod
    def get_file_obj(cls, **kwargs) -> BinaryIO:
        """传入文件名称，返回文件对象"""
        project_id = kwargs.get('project_id')
        file_name = kwargs.get('data')
        file_path = os.path.join(Initialization.get_upload_files(), file_name)
        if os.path.exists(file_path):
            return open(file_path, 'rb')
        else:
            raise FileDoesNotEexistError(*ERROR_MSG_0026)

    @classmethod
    def get_file_path(cls, **kwargs) -> str | list:
        """传入文件名称，返回文件对象"""
        file_name = kwargs.get('data')
        project_id = kwargs.get('project_id')
        HttpApi().download_file(project_id, file_name)
        file_path = os.path.join(Initialization.get_upload_files(), file_name)
        if os.path.exists(file_path):
            return file_path
        else:
            raise FileDoesNotEexistError(*ERROR_MSG_0026)


if __name__ == '__main__':
    print(RandomFileData.get_file_path(**{'data': '文档库搜索112.pdf'}))
