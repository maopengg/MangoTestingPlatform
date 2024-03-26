# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023-01-19 15:27
# @Author : 毛鹏
import os

from PyAutoTest.settings import BASE_DIR


def ensure_path_sep(path: str) -> str:
    """兼容 windows 和 linux 不同环境的操作系统路径 """
    if "/" in path:
        path = os.sep.join(path.split("/"))

    if "\\" in path:
        path = os.sep.join(path.split("\\"))
    return str(BASE_DIR) + path


def nuw_dir():
    file = ['auto_api', 'auto_perf', 'auto_system', 'auto_ui', 'auto_user', 'failure_screenshot']
    logs_dir = ensure_path_sep('/logging_tool')
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    for i in file:
        subdirectory = os.path.join(logs_dir, i)
        if not os.path.exists(subdirectory):
            os.makedirs(subdirectory)


if __name__ == '__main__':
    nuw_dir()
