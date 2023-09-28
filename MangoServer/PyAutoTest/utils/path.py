# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 获取当前文件夹的路径
# @Time   : 2022-11-06 21:28
# @Author : 毛鹏
import os
from typing import Text


def root_path():
    """ 获取 根路径 """
    path = os.path.dirname(__file__)
    return path


def ensure_path_sep(path: Text) -> Text:
    """兼容 windows 和 linux 不同环境的操作系统路径 """
    if "/" in path:
        path = os.sep.join(path.split("/"))

    if "\\" in path:
        path = os.sep.join(path.split("\\"))
    return root_path() + path


if __name__ == '__main__':
    print(ensure_path_sep('log\\log.log'))
    print(ensure_path_sep('cache'))
