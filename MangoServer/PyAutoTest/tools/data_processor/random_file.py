# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-12-21 11:15
# @Author : 毛鹏
import os
from typing import BinaryIO

from PyAutoTest.auto_test.auto_user.service.files_crud import FilesCRUD
from PyAutoTest.exceptions.tools_exception import FileDoesNotEexistError
from PyAutoTest.tools.view_utils.error_msg import ERROR_MSG_0026


class RandomFileData:
    """ 获取文件对象 """

    @classmethod
    def get_file_obj(cls, **kwargs) -> BinaryIO:
        """传入文件名称，返回文件对象"""
        project_id = kwargs.get('project_id')
        file_name = kwargs.get('data')
        file_obj = FilesCRUD(project_id)
        file_path = os.path.join(file_obj.project_upload_folder, file_name)
        if os.path.exists(file_path):
            return open(file_path, 'rb')
        else:
            raise FileDoesNotEexistError(*ERROR_MSG_0026)

    @classmethod
    def get_file_path(cls, **kwargs) -> str:
        """传入文件名称获取文件路径"""
        project_id = kwargs.get('project_id')
        file_name = kwargs.get('data')
        file_obj = FilesCRUD(project_id)
        file_path = os.path.join(file_obj.project_upload_folder, file_name)
        if os.path.exists(file_path):
            return file_path
        else:
            raise FileDoesNotEexistError(*ERROR_MSG_0026)


if __name__ == '__main__':
    RandomFileData.get_file(**{'project_id': 11, 'file_name': '阿达瓦打的阿达片段-1.pdf'})
