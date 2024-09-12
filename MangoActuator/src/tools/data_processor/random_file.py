# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-12-21 11:15
# @Author : 毛鹏
import os

from src.exceptions.error_msg import ERROR_MSG_0026
from src.exceptions.tools_exception import FileDoesNotEexistError
from src.network.http.http_client import HttpClient
from src.tools import InitPath


class RandomFileData:
    """获取文件对象"""

    @classmethod
    def get_file(cls, **kwargs) -> str:
        """传入文件名称，返回文件"""
        file_name = kwargs.get('data')
        HttpClient().download_file(file_name)
        file_path = os.path.join(InitPath.upload_files, file_name)
        if os.path.exists(file_path):
            return file_path
        else:
            raise FileDoesNotEexistError(*ERROR_MSG_0026)


if __name__ == '__main__':
    print(RandomFileData.get_file_path(**{'data': '文档库搜索112.pdf'}))
