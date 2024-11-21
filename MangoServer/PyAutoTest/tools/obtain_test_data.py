# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-19 11:36
# @Author : 毛鹏
from PyAutoTest.exceptions import ERROR_MSG_0026, ToolsError
from mangokit import DataProcessor


class ObtainTestData(DataProcessor):

    def __init__(self):
        super().__init__()

    @classmethod
    def get_file(cls, **kwargs) -> None:
        """传入文件名称，返回文件对象"""
        file_name = kwargs.get('data')
        raise ToolsError(*ERROR_MSG_0026, value=(file_name,))


if __name__ == '__main__':
    pass
