# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023-03-05 20:39
# @Author : 毛鹏
import os

import sys


class InitPath:
    file = ['log', 'screenshot', 'upload_files', 'videos']
    current_directory = os.path.abspath(__file__)
    project_root_directory = os.path.dirname(os.path.dirname(os.path.dirname(current_directory)))
    current_dir2 = os.path.dirname(sys.executable)
    if 'python.exe' not in sys.executable:
        project_root_directory = current_dir2
    logs_dir = os.path.join(project_root_directory, "logs")
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    cache = os.path.join(project_root_directory, "cache")
    if not os.path.exists(cache):
        os.makedirs(cache)
    for i in file:
        subdirectory = os.path.join(logs_dir, i)
        if not os.path.exists(subdirectory):
            os.makedirs(subdirectory)
    log_dir = os.path.join(logs_dir, "log")
    failure_screenshot_file = os.path.join(logs_dir, "screenshot")
    upload_files = os.path.join(logs_dir, 'upload_files')
    videos = os.path.join(logs_dir, 'videos')

    @classmethod
    def get_root_path(cls):
        if getattr(sys, 'frozen', False):
            # 如果是打包后的应用
            return sys._MEIPASS
        else:
            # 如果是源码运行
            return InitPath.project_root_directory

    @classmethod
    def set_svg_icon(cls, icon_name: str):
        app_path = os.path.abspath(os.getcwd())
        folder = rf'{cls.project_root_directory}/resources/icons/'
        path = os.path.join(app_path, folder)
        icon = os.path.normpath(os.path.join(path, icon_name))
        return icon


if __name__ == '__main__':
    print(InitPath.project_root_directory)
    print(InitPath.get_root_path())
    print(InitPath.current_dir2)
    print(InitPath.logs_dir)
    print(InitPath.cache)
    print(InitPath.log_dir)
    print(InitPath.failure_screenshot_file)
    print(InitPath.upload_files)
    print(InitPath.videos)
