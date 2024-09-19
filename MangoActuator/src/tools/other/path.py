# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 获取当前文件夹的路径
# @Time   : 2022-11-06 21:28
# @Author : 毛鹏
import os


class Path:

    @classmethod
    def root_path(cls):
        """ 获取根路径 """
        path = os.path.dirname(__file__)
        return path

    @classmethod
    def ensure_path_sep(cls, path: str) -> str:
        """兼容 windows 和 linux 不同环境的操作系统路径 """
        if "/" in path:
            path = os.sep.join(path.split("/"))

        if "\\" in path:
            path = os.sep.join(path.split("\\"))
        return path


if __name__ == '__main__':
    print(Path.root_path())
