# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 获取当前文件夹的路径
# @Time   : 2022-11-06 21:28
# @Author : 毛鹏
import os

from src import settings


class FilePath:

    @classmethod
    def root_path(cls):
        """ 获取根路径 """
        path = os.path.dirname(__file__)
        return path

    @classmethod
    def auto_ensure_path_sep(cls, path: str) -> str:
        """兼容 windows 和 linux 不同环境的操作系统路径 """
        if "/" in path:
            path = os.sep.join(path.split("/"))

        if "\\" in path:
            path = os.sep.join(path.split("\\"))
        return str(settings.BASE_DIR) + path

    @classmethod
    def ensure_path_sep(cls, path: str) -> str:
        file_path = path.replace('/', os.sep)
        return file_path.replace('\\', '/')


if __name__ == '__main__':
    print(FilePath.ensure_path_sep('/files'))
