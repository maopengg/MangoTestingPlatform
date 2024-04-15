# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023-03-05 20:39
# @Author : 毛鹏
import os

import sys


class Initialization:
    file = ['log', 'screenshot', 'upload_files']
    current_directory = os.path.abspath(__file__)
    project_root_directory = os.path.dirname(os.path.dirname(current_directory))
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
    home_directory = project_root_directory

    @classmethod
    def get_home_directory(cls):
        return cls.home_directory

    @classmethod
    def get_log_screenshot(cls):
        return cls.failure_screenshot_file

    @classmethod
    def get_upload_files(cls):
        return cls.upload_files

    @classmethod
    def get_logs(cls):
        return cls.logs_dir
