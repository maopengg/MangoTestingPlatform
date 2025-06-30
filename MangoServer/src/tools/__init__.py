# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-01-19 15:27
# @Author : 毛鹏
import os

import sys

from src.settings import BASE_DIR


class ProjectDir:

    def __init__(self):
        self.folder_list = ['logs', 'mango-file', 'failed_screenshot', 'upload_template', 'download']
        self._root_path = BASE_DIR
        self.init_folder()

    @staticmethod
    def init_project_path():
        current_directory = os.path.abspath(__file__)
        project_root_directory = os.path.dirname(os.path.dirname(os.path.dirname(current_directory)))
        current_dir2 = os.path.dirname(sys.executable)
        if 'python.exe' not in sys.executable:
            project_root_directory = current_dir2
        return project_root_directory

    def init_folder(self):
        for i in self.folder_list:
            file = os.path.join(self._root_path, i)
            if not os.path.exists(file):
                os.makedirs(file)
        logs_dir = os.path.join(self._root_path, 'logs')
        for i in ['auto_api', 'auto_perf', 'auto_system', 'auto_ui', 'auto_user', 'auto_pytest']:
            subdirectory = os.path.join(logs_dir, i)
            if not os.path.exists(subdirectory):
                os.makedirs(subdirectory)

    def root_path(self):
        return self._root_path

    def logs(self, folder_name='logs'):
        return os.path.join(self._root_path, folder_name)

    def download(self, folder_name='download'):
        return os.path.join(self._root_path, folder_name)

project_dir = ProjectDir()

if __name__ == '__main__':
    print(project_dir.logs())
    print(project_dir.root_path())
