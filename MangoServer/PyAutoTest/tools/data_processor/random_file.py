# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-12-21 11:15
# @Author : 毛鹏

from PyAutoTest.exceptions.tools_exception import FileDoesNotEexistError
from PyAutoTest.exceptions.error_msg import ERROR_MSG_0026


class RandomFileData:
    """ 获取文件对象 """

    @classmethod
    def get_file(cls, **kwargs) -> None:
        """传入文件名称，返回文件对象"""
        file_name = kwargs.get('data')
        raise FileDoesNotEexistError(*ERROR_MSG_0026, value=(file_name,))


if __name__ == '__main__':
    RandomFileData.get_file(**{'project_id': 11, 'file_name': '阿达瓦打的阿达片段-1.pdf'})
