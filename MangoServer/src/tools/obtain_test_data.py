# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-19 11:36
# @Author : 毛鹏
from mangotools.data_processor import DataProcessor
from src.exceptions import ERROR_MSG_0026, ToolsError


class ObtainTestData(DataProcessor):

    @classmethod
    def get_file(cls, **kwargs) -> None:
        """传入文件名称，返回文件对象"""
        file_name = kwargs.get('data')
        raise ToolsError(*ERROR_MSG_0026, value=(file_name,))


if __name__ == '__main__':
    pass
