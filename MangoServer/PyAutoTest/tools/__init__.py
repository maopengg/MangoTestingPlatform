# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-01-19 15:27
# @Author : 毛鹏
import os


def ensure_path_sep(path: str) -> str:
    from PyAutoTest.settings import BASE_DIR
    """兼容 windows 和 linux 不同环境的操作系统路径 """
    if "/" in path:
        path = os.sep.join(path.split("/"))

    if "\\" in path:
        path = os.sep.join(path.split("\\"))
    return str(BASE_DIR) + path


def nuw_dir():
    for i in ['/logs', '/test_file', '/failed_screenshot', '/upload_template']:
        file = ensure_path_sep(i)
        if not os.path.exists(file):
            os.makedirs(file)

    logs_dir = ensure_path_sep('/logs')
    for i in ['auto_api', 'auto_perf', 'auto_system', 'auto_ui', 'auto_user']:
        subdirectory = os.path.join(logs_dir, i)
        if not os.path.exists(subdirectory):
            os.makedirs(subdirectory)


if __name__ == '__main__':
    nuw_dir()
